# ૨૧. Vault અને Rules Modules — શા માટે, કેવી રીતે, કોની સાથે જોડાયેલ (Gujarati Explainer)

> Source: `services/gxp-api/app/modules/vault/{models,service,commands,router}.py`,
> `services/gxp-api/app/modules/rules/{models,service,commands,expression,precision,uom_commands,router}.py`,
> `frontend/src/app/{vault,rules}/page.tsx`, `services/gxp-api/scripts/seed.py` (permission/role matrix).
>
> આ document બીજા documents (૦૬-૦૮, ૧૪) ની જેમ "step-by-step demo walkthrough" નથી — તે **બે cross-
> cutting module ની architecture સમજૂતી** છે, જે લગભગ **દરેક બીજા module ની નીચે** કામ કરે છે.

---

## ૨૧.૧ બે લીટીમાં ફરક

| | Vault | Rules |
|---|---|---|
| શું છે | **"શું થયું તેનો કાયમી પુરાવો"** — release થયેલ દરેક master record ની immutable, hash-verified snapshot history | **"કેવી રીતે નિર્ણય/ગણતરી થાય"** — formula (rule) અને unit-conversion (UOM) ને versioned, signed, released data તરીકે manage કરે |
| Analogy | Notary/vault locker — એક વાર sign થયેલ document ને કાયમ માટે લોક કરીને રાખે | Calculator engine — "95% થી વધારે yield = PASS" જેવા formula ને code માં hardcode કરવાને બદલે data તરીકે release કરે |
| Table | `vault.gxp_vault_object`, `vault.gxp_vault_evidence`, `vault.gxp_record_correction` | `rules.gxp_rule_definition`, `rules.gxp_rule_evaluation`, `rules.gxp_uom`, `rules.gxp_uom_conversion` |

---

## ૨૧.૨ Vault Module

### શા માટે જરૂરી છે?
21 CFR Part 11 / GxP નિયમ કહે છે — એક વાર regulated record (Product, Recipe, Batch, QC Spec, Document...)
**sign/release** થાય, પછી તેને **ક્યારેય edit ના કરી શકાય**. `CLAUDE.md` ના non-negotiable AG-08 ("Audit/
Vault/evidence history is immutable and superseding") અને hard prohibition "No UPDATE/DELETE on audit,
signature, vault or evidence rows" આ જ વસ્તુ enforce કરે છે. Vault એ જ "legal snapshot store" છે જે આ
guarantee આપે છે.

### કેવી રીતે કામ કરે છે?
- **`VaultObject`** (`vault/models.py:12`) — દરેક release ની નવી row, જૂની row **ક્યારેય UPDATE નહીં**:
  - `canonical_payload` (JSONB) = તે ક્ષણનો સંપૂર્ણ data snapshot
  - `digest` = SHA-256 hash — tampering પકડવા માટે
  - `internal_version` = 1, 2, 3... (દરેક નવું release = +1)
  - `supersedes_object_id` = અગાઉના version સાથે chain link (hash-chain જેમ audit trail માં)
  - `corrected_from_object_id` = જો આ release એક correction નું પરિણામ હોય
- **`release_master()`** (`vault/service.py:20`) — callerના domain command ની **એ જ DB transaction**
  માં ચાલે છે (AG-06) — product/recipe/batch release અને vault snapshot એક જ atomic commit.
  `UNIQUE(object_type, business_id, internal_version)` constraint concurrent release ને સુરક્ષિત કરે છે
  (`ConcurrentVaultReleaseError` — retryable).
- **`verify_integrity()`** (`vault/service.py:117`) — digest ફરી compute કરીને data ચકાસે + chain link
  (`supersedes_object_id`) સાચો છે કે નહીં — બરાબર audit module ના "verify hash chain" જેવું જ pattern,
  પણ vault object પર.
- **`RecordCorrection`** (`vault/models.py:66`) — released record માં ભૂલ મળે તો edit નહીં:
  `request_correction` → **2-signature ceremony** (corrector + independent QA Releaser approver,
  `vault/commands.py::complete_correction`) → નવું superseding version બને.

### Permission Matrix (seed.py)

| Permission | કોને મળેલ | શું કરી શકે |
|---|---|---|
| `vault.review` | Admin, QA Reviewer, QA Releaser, QC Reviewer | Version history જોવી, integrity verify કરવી |
| `vault.correct` | Admin, QA Releaser | Generic release endpoint, correction request/complete |

### Frontend (`/vault`) — ખરેખર શું બતાવે છે
- Lookup form: Record type dropdown + Business ID → version history table (version, status, released
  at, supersedes, "View" button).
- **ધ્યાન રાખો:** dropdown માં ફક્ત ૩ object type છે — `OBJECT_TYPES = ["batch", "material_lot", "rule"]`
  (`frontend/src/app/vault/page.tsx:54`). નીચે ૨૧.૪ માં જુઓ — backend ખરેખર ૧૫+ object type save કરે છે,
  પણ UI dropdown માંથી ફક્ત આ ૩ જ select કરી શકાય (business ID manually type કરીને બીજા types ની lookup
  theoretically શક્ય છે, dropdown માં option ઉમેરવી પડે).
  છતાં, `vault.correct` હોય (Admin/QA Releaser) તેને "Complete a correction" કાર્ડ અને generic
  "Release a master record" signed form પણ દેખાય છે.

---

## ૨૧.૩ Rules Module

### શા માટે જરૂરી છે?
Manufacturing/QC ના ઘણા નિર્ણયો calculation પર આધારિત છે (દા.ત. "yield % ≥ 95%?", "spray force spec
range માં?"). જો formula code માં hardcode કરેલ હોય, તો formula બદલવા માટે **deployment + revalidation**
જોઈએ. Rules module formula ને **versioned, signed, released reference data** તરીકે રાખે છે — નવું
version release થાય તો જૂના batches જૂના rule version થી જ evaluate થયેલા **કાયમ રહે** (`RuleEvaluation`
append-only, RUL-FR-022 — historical result ફરી-calculate ક્યારેય નહીં થાય). આ AG-15 ("No regulated
behavior is guessed") ને સપોર્ટ કરે.

### કેવી રીતે કામ કરે છે — બે ભાગ

**A. Rule Engine**
- **`RuleDefinition`** (`rules/models.py:13`) — lifecycle: `draft → validated → released` (released
  પછી અચલ) → `superseded/retired`. દરેક rule માં ફરજિયાત: `expression_ast` (formula), `unit_policy`,
  `precision_policy`, `rounding_policy`.
- **`evaluate_rule()`** (`rules/commands.py:482`) — caller ના inputs લઈને:
  1. effective released rule version શોધે (`get_effective_released_rule`)
  2. unit conversion લાગુ કરે (`_apply_unit_policy`)
  3. formula evaluate કરે (`expression.py::evaluate`)
  4. Document 110 ની precision/rounding policy મુજબ result round કરે
  5. **`RuleEvaluation`** row માં result કાયમ માટે save કરે — outcome `PASS`/`FAIL`/`COMPUTED`/`ERROR`

**B. UOM (Unit of Measure) Master**
- **`UnitOfMeasure`** + **`UomConversion`** (`rules/models.py:81,108`) — "kg", "mg", "mL" જેવા units ને
  released reference data તરીકે રાખે. `resolve_uom()`/`resolve_conversion()` fail-closed છે — unit ન મળે
  તો `UOM_UNKNOWN`/`UOM_CONVERSION_UNAVAILABLE` error, silently pass નહીં.
- UOM/conversion નું release પણ Vault માં જાય જ (`object_type="uom"` / `"uom_conversion"`,
  `rules/uom_commands.py:195,342`) — rule ની જેમ જ pattern.

### Permission Matrix (seed.py)

| Permission | કોને મળેલ | શું કરી શકે |
|---|---|---|
| `rules.author` | **Admin only** | Rule/UOM/conversion draft, validate, simulate |
| `rules.release` | Admin, QA Releaser | Validated rule/UOM/conversion release |
| `rules.evaluate` | Admin, Operator, Supervisor, QA Reviewer, QA Releaser, QC Reviewer, Process Engineer (લગભગ બધા operational roles) | Released rule evaluate કરવી (batch/QC/DDCP ની પોતાની command ના ભાગ રૂપે) |

> **નોંધ:** `rules.author`/`rules.release` ફક્ત Admin + QA Releaser પાસે છે — Process Engineer પાસે પણ
> rule **author** કરવાની પરમિશન નથી (ફક્ત `rules.evaluate` છે). એટલે નવું calculation rule બનાવવું એ
> Admin-level કાર્ય છે, process authoring કાર્ય નહીં.

### Frontend (`/rules`) — ખરેખર શું બતાવે છે
ત્રણ section: **Rules** (list, New draft, Validate/Simulate/Release), **Units of measure** (list, New
UOM draft, Release), **UOM conversions** (list, New draft, Release). Rule detail modal માં
`expression_ast` JSON panel (raw formula જોઈ શકાય) + Release action signed ceremony સાથે.

---

## ૨૧.૪ કયા મોડ્યુલ સાથે જોડાયેલ છે, અને શા માટે

### Vault — "release" કરતા દરેક module સાથે

| Calling Module | `object_type` | ક્યાં (code) |
|---|---|---|
| Product Master | `product_version`, `constituent_compatibility` | `product_master/commands.py:769,861` |
| Recipe Master | `recipe_version` | `recipe_master/commands.py:891` |
| Material Specification | `material_specification_version` | `material_specification/commands.py:317` |
| Material | `material_coa` | `material/commands.py:597` |
| Batch Execution | `batch_execution_snapshot` | `batch_execution/commands.py:308` |
| QC | `qc_test_specification`, `qc_method_version` | `qc/commands.py:311,491` |
| Release | `release_package` | `release/commands.py:240` |
| QMS Documents | `controlled_document_version` | `qms/document_commands.py:276` |
| Rules (UOM) | `uom`, `uom_conversion` | `rules/uom_commands.py:195,342` |
| Postmarket | `postmarket_surveillance_metric_snapshot`, `postmarket_periodic_safety_dataset`, `postmarket_regulatory_evidence_package` | `postmarket/{commands,reportability_commands}.py` |
| Validation | `validation_master_plan`, `requirement_baseline` | `validation/commands_{plan,trace}.py` |

**શા માટે connect:** દરેક module પોતાની DB table માં status update કરે (દા.ત. `product_version.
lifecycle_state = "released"`) — પણ regulatory legal proof માટે **એ જ transaction** માં Vault માં
immutable copy પણ બને (ઉદા: `product_master/commands.py:767-792` — signature પછી
`vault_service.release_master()` call, પછી `version.released_vault_object_id` + `version.version_hash`
પોતાની table માં save). જો કોઈ પૂછે "આ product version ૬ મહિના પહેલા exactly શું data સાથે release
થયું હતું" — જવાબ domain table માંથી નહીં (એ update થઈ શકે), Vault માંથી આવે (એ ક્યારેય update નથી
થતું).

### Rules — calculation/decision જરૂરી હોય તેવા દરેક module સાથે

| Calling Module | શું માટે વાપરે | ક્યાં (code) |
|---|---|---|
| QC | Acceptance criteria evaluate (PASS/FAIL) | `qc/commands.py:971` (`_evaluate_acceptance`) |
| DDCP | Device-specific calculation (inhalation/coated-device/injector) | `ddcp/{commands,inhalation_commands,coated_device_commands,injector_commands}.py` |
| Yield Reconciliation | Yield % formula | `yield_reconciliation/commands.py:233,335` |
| Material | Release-gate evaluation | `material/commands.py:1493` |
| Batch Execution, Product Master, Recipe Master, Genealogy, QMS (risk) | UOM resolve/convert (quantity units સાચા રાખવા) | `*/uom_backfill.py`, `resolve_uom`/`resolve_conversion` calls |

**શા માટે connect:** આ modules પોતે formula/unit logic લખતા નથી — Rules ને **"ભરોસાપાત્ર calculator"**
તરીકે call કરે. `ddcp/commands.py:18` ના comment માં જ સ્પષ્ટ લખ્યું છે: "rules engine
(`rules.commands.evaluate_rule`) the same way `qc.commands._evaluate_acceptance` does" — એટલે PASS/FAIL
નો નિર્ણય **એક જ, signed, auditable rule version** માંથી આવે, છૂટાછવાયા હાર્ડકોડેડ `if` statements માંથી
નહીં. Unit conversion માટે પણ એ જ કારણ — kg vs g, mL vs L ભેગા કરતી વખતે ભૂલ ન થાય, logic ક્યાંય
copy-paste ન થાય.

### Vault ↔ Rules — એકબીજા સાથે કેવી રીતે જોડાયેલ
Rules module પોતે regulated master data હોવાથી, rule/UOM/conversion release થાય ત્યારે **Rules પોતે
Vault ને call કરે** (`rules/commands.py`, `rules/uom_commands.py` બંને vault import કરે છે). એટલે:

```
Rules  → નિર્ણય/ગણતરી કેવી રીતે થાય તે નક્કી કરે (PASS/FAIL, kg→g)
Vault  → એ નિર્ણય/formula ક્યારે releases થયું તેનો કાયમી પુરાવો રાખે
```

બંને મળીને `CLAUDE.md` §૩ ના regulated mutation path ("...→ ONE PostgreSQL transaction: domain state +
record version + audit event + outbox event") ના "immutable evidence" ભાગને પૂરો કરે છે.

---

## ૨૧.૫ Mini Demo Walkthrough (Live Dataset વાપરીને)

Dataset: Product `MJ-PFS-40MG`, Recipe `RCP-MJ-PFS-V1` (master index §૩ જુઓ).

1. `qa.releaser` login → `/product-master` → `MJ-PFS-40MG` ને release કરો (જો પહેલેથી released ના હોય).
2. `admin` અથવા `qa.reviewer` login → `/vault` → Record type = `batch` અથવા manually business ID type
   કરીને product version ની lookup કરવી try કરો (dropdown limitation ૨૧.૨ માં નોંધેલ).
3. Version row પર "View" → `canonical_payload` JSON અને `digest` જુઓ. "Verify integrity" option હોય તો
   ચકાસો digest valid છે.
4. `admin` login → `/rules` → Units of measure tab → નવું UOM draft (દા.ત. કોઈ નવું unit) બનાવો → release
   (`qa.releaser` પણ release કરી શકે).
5. QC sample result record કરતી વખતે (`/qc`) — background માં `rules_commands.evaluate_rule` call થાય
   છે જે spec rule evaluate કરીને PASS/FAIL નક્કી કરે — result `RuleEvaluation` table માં કાયમ માટે save
   રહે.

---

## ૨૧.૬ ધ્યાન રાખવા જેવી બાબતો (Known Limitations — code વાંચીને ચકાસેલ)

1. **Vault lookup dropdown અધૂરું:** frontend `OBJECT_TYPES` ફક્ત `["batch", "material_lot", "rule"]`
   ધરાવે (`frontend/src/app/vault/page.tsx:54`), જ્યારે backend ૧૫+ object types save કરે છે
   (`product_version`, `recipe_version`, `material_specification_version`, `uom`, `uom_conversion`,
   `controlled_document_version`, `qc_test_specification`, `qc_method_version`, `release_package`,
   `constituent_compatibility`, `material_coa`, `batch_execution_snapshot`, postmarket/validation types
   સહિત). એટલે UI dropdown થી સીધા product/recipe/document version ની vault history select ના કરી
   શકાય — business ID manually જાણતા હોવ તો lookup field માં type કરવું પડે, dropdown માં option
   ઉમેરવી જોઈએ.
2. **Rule authoring Admin-only:** `rules.author` ફક્ત Admin પાસે છે — Process Engineer (જે
   Product/Recipe/Material Spec author કરે છે) પાસે rule બનાવવાની પરમિશન નથી. નવું calculation rule
   જોઈતું હોય તો Admin involve કરવો પડે — by design (seed.py પ્રમાણે), bug નથી.
3. **UOM/UOM-conversion ને કોઈ dedicated demo document નથી** — આ document જ પહેલું છે જે તેમને cover
   કરે છે; master index ના બીજા document (૦૩, ૦૭, ૦૮) માં UOM ફક્ત field-level ઉપયોગ તરીકે mention
   થયેલ છે.
