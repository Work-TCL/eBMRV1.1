# Batch Execution — Field & Permission Reference (Frontend + Backend, Gujarati)

**હેતુ:** આ document `Batch_Create_Execution_Process_Guide_Gujarati.md` નો process flow **ધારી લે છે**
(એ પહેલા વાંચો) — અહીં ફક્ત **દરેક field ક્યાંથી આવે છે, backend માં કયું column/type છે, અને કયો role
એને access કરી શકે** — સંપૂર્ણ technical reference. Developer/QA/client tech team માટે.

**⚠️ પ્રામાણિકતા નોંધ (CLAUDE.md §5):** દરેક field/endpoint/permission `services/gxp-api/app/modules/
batch_execution/{router,commands,models}.py` અને `frontend/src/app/batch-execution/page.tsx` માંથી
code-verified (2026-09-17) છે.

---

## અનુક્રમણિકા

1. [Entity map — 1 નજરમાં](#1-entity-map--1-નજરમાં)
2. [Batch (`gxp_batch`) — દરેક field](#2-batch-gxp_batch--દરેક-field)
3. [Batch Step (`gxp_batch_step`) — દરેક field](#3-batch-step-gxp_batch_step--દરેક-field)
4. [Step Detail sub-entities](#4-step-detail-sub-entities)
5. [Step Result (`gxp_step_result`) — દરેક field](#5-step-result-gxp_step_result--દરેક-field)
6. [Evidence Link, Correction, Hold, Handover, Comment](#6-evidence-link-correction-hold-handover-comment)
7. [Endpoint × Permission × Role — સંપૂર્ણ matrix](#7-endpoint--permission--role--સંપૂર્ણ-matrix)
8. [Frontend page/component map](#8-frontend-pagecomponent-map)
9. [Error code reference](#9-error-code-reference)

---

## 1. Entity map — 1 નજરમાં

```
gxp_batch  (1) ──< (many)  gxp_batch_step
                                 │
                                 ├──< gxp_step_result           (Record results)
                                 ├──< gxp_step_result_correction (Correct → Approve)
                                 ├──< gxp_step_evidence_link     (Link evidence)
                                 ├──< gxp_batch_step_hold        (Hold → Resume, step-scope)
                                 ├──< gxp_batch_step_comment     (Comment)
                                 └──< gxp_batch_step_handover    (Hand over)

gxp_batch_step ──> RecipeStep (frozen recipe-graph reference — instruction/parameters/material+equipment
                                requirements/evidence requirements/dependencies, read-only at execution
                                time, display-only via `execution-view`'s `step_detail_by_step_id`)
```

**Authoritative store (AG-03):** PostgreSQL, schema `ebmr`, code `services/gxp-api/app/modules/
batch_execution/models.py`. **Owning module:** `batch_execution`. Recipe-side (RecipeStep/Parameter/
MaterialRequirement/EquipmentRequirement/EvidenceRequirement/Dependency) owned by `recipe_master` — batch
execution ફક્ત read કરે છે (FK, cross-module), write નથી કરતું.

---

## 2. Batch (`gxp_batch`) — દરેક field

| Field (API) | Backend column | Type | ક્યાંથી set થાય | Frontend માં ક્યાં |
|---|---|---|---|---|
| `batch_id` | `id` | UUID (PK) | Server-generated | `IdFact` "Batch ID" + copy/Open-in-DDCP બટન |
| `site_id` | `site_id` | UUID FK → `iam.sites` | Create form (site context) | hidden, `useSiteId()` |
| `batch_number` | `batch_number` | string, unique | Create form, free text | "New batch" modal |
| `product_version_id` | `product_version_id` | UUID FK → `product_master.product_versions` | Create form — Product/Product version 2-step dropdown | "New batch" modal |
| `product_name`/`product_code` | *(joined, not a column)* | string | Server join, GET only | Batch list/detail (resolved label) |
| `recipe_version_id` | `recipe_version_id` | UUID FK → `recipe_master.recipe_versions` | Create form — Recipe/Recipe version 2-step dropdown | "New batch" modal |
| `recipe_code`/`recipe_version_no` | *(joined)* | string/int | Server join, GET only | Batch list/detail |
| `recipe_vault_object_id` | `recipe_vault_object_id` | UUID, nullable | **Issue** સમયે set — frozen recipe snapshot ID | `IdFact` "Recipe vault object" |
| `execution_snapshot_id` | `execution_snapshot_id` | UUID, nullable | **Issue** સમયે set | `IdFact` "Execution snapshot" |
| `target_qty` | `target_qty` | Numeric(24,8) — **decimal, ક્યારેય float નહીં** (AG-15/DATA-FR-019) | Create form | "New batch" modal |
| `target_uom` | `target_uom` | string | Create form, free text | "New batch" modal |
| `state` | `state` | string enum | Server-managed state machine | `WorkflowStatePill` |
| `version` | `version` | bigint (optimistic concurrency, MUT-FR-009) | Server, every mutation `+1` | Fact "Record version" |
| `production_order_ref` | `production_order_ref` | string, nullable | Create form, optional free text | "New batch" modal |
| `issued_at` / `started_at` | `issued_at` / `started_at` | timestamptz, nullable | Server, Issue/Start action સમયે | Fact "Issued"/"Started" |

**`state` — allowed values (code: `models.py::BATCH_STATES`):**
`planned → issued → in_execution → on_hold → aborted → production_complete`.
**Transition table (`ALLOWED_TRANSITIONS`):** `planned→[issue]`, `issued→[start, abort]`,
`in_execution→[hold, abort]`, `on_hold→[resume, abort]`, `production_complete→[hold]`. બીજી કોઈ પણ
transition `INVALID_TRANSITION` (409).

---

## 3. Batch Step (`gxp_batch_step`) — દરેક field

| Field (API) | Backend column | Type | ક્યાંથી આવે | Frontend માં ક્યાં |
|---|---|---|---|---|
| `step_id` | `id` | UUID (PK) | Server, **Issue** સમયે recipe ના દરેક step માટે 1 row બને | — |
| `batch_id` | `batch_id` | UUID FK | Server | — |
| `recipe_step_code` | `recipe_step_code` | string (દા.ત. `FILL-01`) | Recipe ના `stable_step_code` પરથી frozen | Step ટેબલ નું "Step" column |
| `required_role_code` | `required_role_code` | string, nullable | Recipe author એ declare કરેલો role, **frozen at Issue** | Step ટેબલ "Required role" |
| `required_qualification_code` | `required_qualification_code` | string, nullable | Recipe author, frozen at Issue | Step Detail modal |
| `scope_type`/`scope_id` | `scope_type`/`scope_id` | string/UUID | Recipe's area/equipment scope, frozen | — |
| `state` | `state` | string enum | Server state machine | `WorkflowStatePill` |
| `version` | `version` | bigint | Server, every mutation `+1` | — |
| `assigned_subject_id` | `assigned_subject_id` | UUID FK → `iam.users`, nullable | Start/Hand over સમયે set | "Assigned" column (name+username resolved) |
| `started_at`/`completed_at` | `started_at`/`completed_at` | timestamptz, nullable | Server | Step ટેબલ |

**`state` — allowed values (code: `models.py`):**
`pending → ready → in_progress → complete` + `on_hold` (side-branch, ફક્ત `in_progress` માંથી જ, §11 ના
main guide માં diagram). **Readiness rule (BAT-FR-006):** predecessor-free step batch Start થતાં જ
`ready`; predecessor-વાળો step **બધા** predecessor `complete` થાય ત્યારે `pending → ready`.

---

## 4. Step Detail sub-entities

`GET /batches/v1/{batch_id}/execution-view` નો `step_detail_by_step_id[step_id]` — recipe graph માંથી
**read-only** (regulated decision નથી, ફક્ત display — authoritative instruction Vault ના frozen snapshot
માં જ છે, VLT-FR-006/007):

| Field | Source entity | Type |
|---|---|---|
| `step_type` | `RecipeStep.step_type` | enum (16 value — Batch_Create_Execution_Process_Guide_Gujarati.md §16.3 ના `weigh`/`assembly`/`test`/વગેરે) |
| `instruction_text` | `RecipeStep.instruction_text` | text |
| `is_critical` | `RecipeStep.is_critical` | boolean |
| `sequence_hint` | `RecipeStep.sequence_hint` | int |
| `section_code`/`section_name` | `RecipeSection` | string |
| `expected_hold_duration_minutes` | `RecipeStep.expected_hold_duration_minutes` | int, nullable |
| `predecessor_codes`/`successor_codes` | `RecipeDependency` graph | string[] |
| `evidence_requirements[]` | `RecipeEvidenceRequirement` | `evidence_type`, `required_count`, `allowed_mime_types`, `retention_class` |
| `material_requirements[]` | `RecipeMaterialRequirement` (+ joined `MaterialSpecificationVersion`) | `material_spec_version_id`, `material_spec_business_id`, `material_name`, `target/min/max_value`, `uom`, `consume_mode`, `substitution_allowed`, `genealogy_required` |
| `equipment_requirements[]` | `RecipeEquipmentRequirement` | `equipment_class`, `exact_equipment_optional`, `require_current_calibration`, `require_current_qualification`, `require_current_cleaning` |

**`parameters_by_step_id[step_id][]`** (`RecipeParameter`, "Record results" form ના fields): `parameter_
code`, `data_type` (decimal/integer/text/boolean), `uom`, `target_value`/`min_value`/`max_value`,
`precision_digits`, `required`. *(`rule_id`/`rule_version` પણ stored છે પણ `execution-view` response માં
પરત નથી થતા — batch execution rule ને evaluate પણ નથી કરતું, §17 ના honest gap માં નોંધ્યું છે.)*

---

## 5. Step Result (`gxp_step_result`) — દરેક field

| Field (API) | Backend column | Type | ક્યાંથી આવે |
|---|---|---|---|
| `result_id` | `id` | UUID | Server |
| `parameter_code` | `parameter_code` | string | "Record results" form field name |
| `data_type` | `data_type` | string | Parameter ના data_type પરથી |
| `value_numeric`/`value_text`/`value_bool` | એ જ નામના columns | Decimal/string/bool | User એ ભરેલી actual value (data_type પ્રમાણે 1 જ ભરાય) |
| `uom` | `uom` | string, nullable | Parameter ના uom પરથી |
| `source_type` | `source_type` | string | `manual_entry` (સામાન્ય રીતે) |
| `quality_status` | `quality_status` | `in_range` / `out_of_range` / `not_evaluated` | **Server-computed** (`commands.py::_step_result_quality_status`) — parameter ના min/max સામે. **Informational only — save/Complete ને ક્યારેય block નથી કરતું.** |
| `received_at` | `received_at` | timestamptz | Server |
| `signature_id` | `signature_id` | UUID | દરેક submit = 1 સહી (fresh password reauth) |
| `supersedes_result_id` | `supersedes_result_id` | UUID, nullable | Correction flow (§6) — નવો result જૂનાને supersede કરે, જૂનો delete/edit નથી થતો (AG-08) |

**Multiple submit:** parameter દીઠ multiple result row બની શકે (દરેક પોતાની સહી સાથે) — **છેલ્લી** value
જ `latestByCode` તરીકે UI માં final ગણાય, Complete વખતે પણ છેલ્લી જ ચેક થાય.

---

## 6. Evidence Link, Correction, Hold, Handover, Comment

| Entity | Table | Signed? | Key fields |
|---|---|---|---|
| **Evidence link** | `gxp_step_evidence_link` | ❌ ના (Document 106 માં કોઈ policy row નથી — capture, disposition નહીં) | `evidence_id`, `evidence_version`, `evidence_sha256`, `media_type`, `requirement_code` (evidence_type સાથે match — Complete વખતે આ જ પરથી count ગણાય), `linked_by`, `created_at` |
| **Result correction** | `gxp_step_result_correction` | ✅ Request (reason ફરજિયાત) + ✅ Approve (**independent** — requester ≠ approver) | `original_result_id`, `reason_text`, `corrected_value_*`, `status` (`requested`/`completed`), `requested_by_user_id`, `approved_by_user_id`, `resulting_result_id` |
| **Step hold** | `gxp_batch_step_hold` | ✅ Hold (reason ફરજિયાત, `Performed`) + ✅ Resume (`Approved` meaning — QA-authority ભાવ) | `reason`, `held_at`, `held_by`, `hold_signature_id` |
| **Hand over** | `gxp_batch_step_handover` | ❌ ના | `from_subject_id`, `to_subject_id`, `reason` — **state બદલાતી નથી**, ફક્ત owner |
| **Comment** | `gxp_batch_step_comment` | ❌ ના | `comment_text`, `created_by`, `created_at` |

---

## 7. Endpoint × Permission × Role — સંપૂર્ણ matrix

*(code: `batch_execution/router.py`'s દરેક `evaluate_policy(...)` call. Role ownership:
`scripts/seed.py::ROLE_PERMISSIONS`.)*

| Endpoint | Permission action | Role(s) જે ધરાવે છે |
|---|---|---|
| `POST /batches/v1` (Create) | `batch_execution.create` | Admin, Supervisor |
| `POST /{id}/issue` | `batch_execution.issue` | Admin, Supervisor |
| `POST /{id}/start` | `batch_execution.execute` | Admin, Supervisor, Operator |
| `POST /{id}/hold` / `/resume` / `/abort` (batch-level) | `batch_execution.execute` | Admin, Supervisor, Operator |
| `POST /{id}/production-complete` (+ signature-challenges) | `batch_execution.execute` | Admin, Supervisor, Operator |
| `POST /{id}/signature-challenges` (batch-level) | `batch_execution.execute` | Admin, Supervisor, Operator |
| `POST /{id}/steps/{sid}/start` | `batch_execution.execute` **+ step નો `required_role_code`** (Supervisor/Admin `override_reason` થી override કરી શકે — `batch_step.role_override` permission) | recipe એ declare કરેલો role |
| `POST /{id}/steps/{sid}/signature-challenges` | `batch_execution.execute` | ઉપર મુજબ |
| `POST /{id}/steps/{sid}/results` (Record results) | `batch_execution.execute` + role | ઉપર મુજબ |
| `POST /{id}/steps/{sid}/evidence-links` (Link evidence) | `batch_execution.execute` + role | ઉપર મુજબ |
| `POST /{id}/steps/{sid}/complete` | `batch_execution.execute` + role | ઉપર મુજબ |
| `POST /{id}/steps/{sid}/hold` / `/resume` (step-level) | `batch_execution.execute` + role | ઉપર મુજબ |
| `POST /{id}/steps/{sid}/comments` | `batch_execution.execute` + role | ઉપર મુજબ |
| `POST /{id}/steps/{sid}/handover` | `batch_execution.execute` + role | ઉપર મુજબ |
| `POST /{id}/steps/{sid}/correct` (Request correction) | `batch_step.correct` (command-level check) | Supervisor |
| `POST /{id}/steps/{sid}/corrections/{cid}/approve` | `batch_step.correct` + **independent of requester** | Supervisor (બીજો actor) |
| `GET /batches/v1` (List) | `batch_execution.view` | Admin, Supervisor, Operator, QA Reviewer, QA Releaser, QC Reviewer, DDCP Operator |
| `GET /{id}` (Detail) | `batch_execution.view` | ઉપર મુજબ |
| `GET /{id}/execution-view` | `batch_execution.view` | ઉપર મુજબ |

**⚠️ Step-level role — 2-સ્તરનું gate, ગૂંચવાવ નહીં (code-verified, `_enforce_step_role()`):**
1. પહેલા actor પાસે **`batch_execution.execute`** હોવું જ જોઈએ — આ ફક્ત **Admin/Supervisor/Operator**
   ધરાવે છે. QC Reviewer/QA Reviewer/Sanitation Operator (કે બીજો કોઈ પણ role) **ધરાવતા નથી** — આ
   role નો actor કોઈ પણ step action call કરે તો **base gate પર જ** `403 ROLE_MISSING` આવે, step ના
   `required_role_code` સુધી પહોંચ્યા વગર.
2. Base gate pass થાય પછી જ `required_role_code` (set હોય તો) સામે ચેક થાય — match ના થાય તો
   `STEP_ROLE_MISMATCH` (403), Supervisor/Admin `override_reason` આપીને જ proceed કરી શકે.

**વ્યવહારુ અસર:** Recipe author કોઈ પણ role name `required_role_code` તરીકે પસંદ/ટાઈપ કરી શકે (UI કોઈ
warning નથી આપતું) — પણ Admin/Supervisor/Operator સિવાયનો role point કરે તો એ step **કાયમ માટે execute
ના જ થઈ શકે** (override સિવાય). પૂરી વિગત + real finding →
`Batch_Create_Execution_Process_Guide_Gujarati.md` §16.1 (`RCP-MJ-PFS-V1` v2/v3 આ જ ભૂલ સાથે બન્યા
હતા, v4 એ fix કર્યું — §16.3 નું field table).

---

## 8. Frontend page/component map

| UI element | Component | File |
|---|---|---|
| Batch list + KPI tiles | `BatchExecutionPage` | `frontend/src/app/batch-execution/page.tsx` |
| "New batch" modal | `CreateBatchModal` (Product/Recipe cascading pickers) | એ જ ફાઈલ |
| Batch detail — Facts + step ટેબલ | `BatchDetailModal` | એ જ ફાઈલ |
| Step Detail (instruction/parameters/material+equipment/evidence progress) | `StepDetailModal` | એ જ ફાઈલ |
| Record results | `RecordResultsModal` | એ જ ફાઈલ |
| Link evidence (+ live "N of M" progress) | `LinkEvidenceModal` | એ જ ફાઈલ |
| Hand over | `HandoverStepModal` | એ જ ફાઈલ |
| Step Hold/Resume, batch Hold/Resume/Abort | `SignatureCeremony` વાપરીને inline handlers | એ જ ફાઈલ |
| Result correction request/approve | `CorrectResultModal`/`ApproveCorrectionModal` | એ જ ફાઈલ |
| Batch ID copy / Open in DDCP | `CopyIdButton` + `LinkButton` (`IdFact`'s `action` slot) | એ જ ફાઈલ, `components/ui/FactGrid.tsx` |
| Recipe authoring (§16 ના multi-step recipe આ રીતે બન્યો) | `RecipeGraphEditor`/`StepBlock` | `frontend/src/app/recipe-master/shared.tsx` |

---

## 9. Error code reference

| Code | HTTP | ક્યારે | Fix |
|---|---|---|---|
| `INVALID_TRANSITION` | 409 | Batch/step ખોટી state માં action call | State ચેક કરો, ફરી try |
| `STALE_VERSION` | 409 | `expected_version` current version સાથે match ના થાય | Fresh data reload કરીને ફરી |
| `STEP_ROLE_MISMATCH` | 403 | Actor પાસે step નો required role નથી | Correct role ના user થી, અથવા Supervisor override |
| `PARAMETER_REQUIRED` | 422 | Required parameter નું result record નથી | Record results પહેલા કરો |
| `VALIDATION_FAILED` | 422 | Required evidence link નથી (અથવા બીજી validation) | Link evidence પહેલા કરો |
| `MISSING_SIGNATURE` | 428 | Signed action માટે password/challenge વગર submit | Password ફરી નાખો |
| `PRODUCTION_NOT_COMPLETE` | 422 | Production Complete — બધા step complete નથી | બાકી step list જુઓ, પૂરા કરો |

---

**Cross-reference:** Process flow → `Batch_Create_Execution_Process_Guide_Gujarati.md`. DDCP-specific
fields → `DDCP_Client_Demo_Guide_Gujarati.md`. Open gaps → `docs/generated/18_SPEC_GAPS.md`.
