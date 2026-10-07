# ૧૪. Platform Dashboard, Audit Trail, Evidence, Vault, Documents, Training — Gujarati Demo Guide

> Source: `frontend/src/app/platform/page.tsx`, `frontend/src/components/layout/Sidebar.tsx`,
> `frontend/src/app/{audit,audits,vault,documents,training}/`, backend
> `services/gxp-api/app/modules/{audit,evidence,vault,mutation}/`,
> `services/gxp-api/app/modules/qms/{document_*,training_*}.py`.

---

## ૧૪.૧ Platform Dashboard (`/platform`) શું બતાવે છે

આ પેજ **role પ્રમાણે અલગ** દેખાય છે — બધા user ને એક સરખું નથી દેખાતું:

- **Admin-only કાર્ડ્સ:** Data ownership/dictionary, Projection/read-model health, Backup &amp; disaster
  recovery, Search &amp; read models, Workflow orchestration ops, Async report exports.
- **Admin + Operator + Supervisor + QA Reviewer ને દેખાય છે:** "Evidence operations" (upload/finalize/
  integrity-check/manifest/legal-hold) અને "Download evidence" — કારણ કે backend માં `evidence.upload`/
  `evidence.download` આ ચાર roles ને જ મળેલ છે (Admin ઉપરાંત).
- જે user ન તો Admin છે ન evidence-capable — તેને આ પેજ પરથી સીધું `/batch-execution` પર redirect કરી
  દેવાય છે.

> **ઈતિહાસ:** આ પેજ પહેલા સંપૂર્ણપણે Admin-only gated હતું (SG-204 bug) — Operator/Supervisor/QA
> Reviewer પાસે backend permission હોવા છતાં Evidence cards દેખાતા નહોતા. આ હવે ફિક્સ થયેલ છે
> (2026-09-17) — code comment માં જ documented છે.

## ૧૪.૨ Sidebar Navigation

ડાબી બાજુ Sidebar માં modules groups માં ગોઠવાયેલા છે: Production, Materials &amp; QC, Operations,
Quality system, Integrations, Postmarket, Validation, AI, Compliance, Engineering, Admin. દરેક
section/item નું પોતાનું `show()` gate હોય છે, જે backend permission સાથે verify કરેલ મળ્યું (કોઈ
mismatch નથી મળી — Sidebar ફક્ત UI decide કરે છે, actual authorization દરેક API call પર backend
કરે છે).

---

## ૧૪.૩ Audit Trail — બે અલગ વસ્તુઓ, confuse ના કરવી

| | `/audit` — Audit Ledger | `/audits` — QMS Internal Audits |
|---|---|---|
| શું છે | દરેક regulated write નો technical "who changed what, when" રેકોર્ડ | Facility/process quality audit scheduling + findings (state: SCHEDULED→IN_PROGRESS→FINDINGS_OPEN→CLOSED) |
| Permission | `audit.review` (Admin, QA Reviewer, QA Releaser, QC Reviewer) | અલગ QMS internal-audit permissions |

**Audit Ledger UI (`/audit`):** record ID, actor, record type, site, signed/unsigned, date range થી
filter કરી શકાય, + "Verify hash chain" checkbox. Row click → detail modal: record/version, actor, site,
signature, reason, correlation ID, event hash, previous hash, old/new value diff.

**Audit Event Fields:** `id, site_id, aggregate_type, aggregate_id, aggregate_version, action,
actor_type, actor_id, actor_username, occurred_at, reason, old_value, new_value, changed_fields,
signature_id, correlation_id, prev_event_hash, event_hash`.

**અગત્યની ટેક્નિકલ ડિટેલ (client ને trust build કરવા માટે):** `audit_events` ટેબલ પરનો database
login (application user) પાસે **માત્ર INSERT/SELECT permission છે — UPDATE/DELETE database level પર જ
block છે** (migration `0002_privileges`). એટલે કોઈ પણ — application bug હોય કે direct database access
હોય — audit entry ને ચૂપચાપ બદલી કે delete કરી શકતું નથી.

---

## ૧૪.૪ Evidence અને Vault — બે અલગ ખ્યાલો

**Evidence** = કોઈ પણ regulated action સાથે જોડાયેલ file-based proof (ફોટો, scan, PDF, log).
- Lifecycle: `STAGED → FINALIZED → ARCHIVED` (hash mismatch થાય તો `QUARANTINE`, ફાઇલ ખોવાઈ જાય તો
  `MISSING`)
- **WORM Storage:** ફાઇલ `sha256` hash પ્રમાણે content-addressed store થાય છે — એક જ key પર અલગ bytes
  overwrite કરવાની કોશિશ error આપે છે; write પછી ફાઇલ `read-only` (chmod 0o440) બની જાય છે. Store
  abstraction માં **`delete()` method જ અસ્તિત્વમાં નથી**.
- Upload flow: Stage (`POST /evidence/v1/uploads`) → Finalize (actual file bytes સાથે).
- Download: ફક્ત `FINALIZED`/`ARCHIVED` state ના evidence માટે.
- Permission: `evidence.upload`/`download` → Admin, Operator, Supervisor, QA Reviewer. `evidence.manifest`/
  `legal_hold`/`integrity_check` → Admin, QA Reviewer only.

**Vault (`/vault`)** = દરેક batch release અને material-lot disposition ની **immutable snapshot history**
— version-by-version compare, digest/chain integrity check, correction request. Permission:
`vault.review` (view — Admin, QA Reviewer, QA Releaser, QC Reviewer), `vault.correct` (Admin, QA
Releaser).

---

## ૧૪.૫ Documents (SOP / Document Control)

Controlled Document → Version (state: `DRAFT → REVIEW → RELEASED → EFFECTIVE → SUPERSEDED/OBSOLETE`) →
Controlled Copy (issued/returned/destroyed). Released version ની Vault માં snapshot બને છે (recipe/
product release ની જેમ જ pattern). Version, change control ID સાથે (real FK) જોડાયેલ હોઈ શકે.

| Action | Permission | Role |
|---|---|---|
| Author/Submit document | `document.create`/`submit` | Admin, QA Reviewer |
| Release/Make Effective/Obsolete | `document.release`/etc. | Admin, QA Releaser |

---

## ૧૪.૬ Training Module

Curriculum requirement → per-person Assignment (`ASSIGNED → ASSESSMENT_PENDING → COMPLETED/FAILED`) →
Qualification Record (`QUALIFIED/EXPIRING/EXPIRED/RENEWED`) → Waiver.

| Action | Permission | Role |
|---|---|---|
| Create requirement/assignment | `training.requirement.create`/`assignment.create` | Admin, Supervisor, QA Reviewer |
| Assess / Grant qualification / Waiver | `training.assignment.assess`, `qualification.create`, `waiver.create` | Admin, QA Releaser |

**અગત્યનું — batch execution training-check** સાથે જોડાણ ૧૪.૮ મુદ્દા ૨ માં જુઓ.

---

## ૧૪.૭ Client-facing સમજૂતી — "એક Transaction Guarantee" (plain terms)

જ્યારે પણ સિસ્ટમમાં કોઈ regulated write થાય (evidence upload, batch step complete, document release —
કંઈ પણ), ત્યારે ત્રણ વસ્તુઓ **એક જ database transaction માં એકસાથે** થાય છે:

1. **Actual data change** સેવ થાય.
2. **Audit event** લખાય — જેમાં પાછલા event ના hash ને પણ સામેલ કરીને નવો hash બનાવાય છે (એક hash-chain,
   જેમ blockchain-style ledger). જો કોઈ જૂનો audit entry tamper કરે, તો chain તૂટી જાય — જે `/audit` ના
   "Verify hash chain" બટનથી તરત ખબર પડી જાય.
3. **Outbox event** લખાય — બાકીના સિસ્ટમ (search, notification, integration) ને પછીથી મોકલવા માટે.

**Client માટે સાદી ભાષામાં:** Data change, audit entry, અને "બાકીનાને જણાવવાનું" — ત્રણેય એક જ
transaction માં છે, એટલે crash/network failure/bug ગમે તે થાય, ક્યારેય એવું નહીં થાય કે data બદલાયું
પણ audit trail માં entry ના હોય, અથવા ઊંધું. અને audit ટેબલ database level પર જ UPDATE/DELETE-proof છે
— કોઈ પણ, ડાયરેક્ટ ડેટાબેઝ access ધરાવતી વ્યક્તિ પણ, ચૂપચાપ history બદલી ના શકે.

---

## ૧૪.૮ ધ્યાન રાખવા જેવી બાબતો (Known Limitations)

1. ~~બે "signature ceremony not wired" live bugs~~ **✅ બંને Fixed (2026-09-18):**
   - `/platform` નું "Apply legal hold" evidence form — હવે real `SignedJsonForm` (password re-entry)
     વાપરે છે. Backend માં પણ `POST /evidence/v1/{id}/signature-challenges` endpoint નવો ઉમેરાયો
     (પહેલા અસ્તિત્વમાં જ નહોતો).
   - `/documents` નું "Release" action — હવે real `SignatureCeremony` વાપરે છે (challenge endpoint
     પહેલેથી હતું, ફક્ત frontend wiring missing હતું).

   બંને actions હવે ડેમોમાં live બતાવી શકાય — `qa.reviewer`/`admin` (evidence upload/legal-hold),
   `qa.reviewer` (document submit) → `qa.releaser` (document release).
2. ~~બે અલગ Qualification ledgers જોડાયેલી નથી, `iam.qualifications` માં લખવાનો કોઈ રસ્તો નથી~~
   **✅ Fixed (2026-09-17, SG-086 write-through)** — Training ના "Grant qualification"
   (`POST /training/v1/qualifications`) હવે `qms.qualification_record` ની સાથે-સાથે `iam.qualifications`
   માં પણ row લખે છે (`training_commands.py::create_qualification`). Schema/version reconciliation
   વચ્ચે હજુ ખુલ્લું છે, પણ "લખવાનો રસ્તો જ નથી" હવે ખોટું છે.
3. ~~Vault ની "Request Correction" ઇરાદાપૂર્વક અધૂરી છે, signature policy define નથી~~
   **UI ની જૂની claim ખોટી હતી — backend 2026-09-11 થી જ પૂરું છે** (`record_correction`/`complete`
   signature policy, 2-signer chain: corrector + independent QA Releaser approver,
   `vault/commands.py::complete_correction`). **✅ 2026-09-19 Fixed:** frontend માં "Complete correction"
   UI હવે ઉમેર્યું — પહેલાં ફક્ત "Request correction" જ હતું, already-working backend ceremony સુધી
   કોઈ રસ્તો જ નહોતો.
4. ~~`Supervisor` role માટે કોઈ demo user seed નથી~~ **✅ Fixed (2026-09-18)** — `supervisor1` હવે
   seed થયેલ (ડોક્યુમેન્ટ ૦૨ જુઓ).
