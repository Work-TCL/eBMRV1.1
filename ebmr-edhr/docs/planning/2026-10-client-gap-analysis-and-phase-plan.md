# Client Meeting (2026-10-03/04) — Gap Analysis & Implementation Phase Plan

**Status:** DRAFT — for discussion, not approved. No code, migrations, or data have been changed as part of
producing this document.

**Correction note (same pass):** the initial codebase inventory (an automated search) missed two modules it
wasn't pointed at directly — `app/modules/qc/` and `app/modules/evidence/` — because their names don't match
the client's vocabulary ("QC Testing," "Document upload"). Direct verification afterward found both already
exist and are substantially more mature than the first pass suggested. This materially changes Phase 4 and two
items in §2.7 below from "build new" to "integrate existing" — see the inline notes marked **[CORRECTED]**.

**Inputs:**
- `client-meet/eBMR-03-oct-{1..9}.txt`, `client-meet/eBMR-04-oct-{1,2}.txt` — live walkthrough recordings
  (Gujarati/English) between the platform owner and a client, working through Company/Site setup → Users/Roles →
  Supplier → Material → Material Receipt/QC → Equipment → (Product Master, cut short by time).
- Live codebase inventory: `services/gxp-api/app/modules/*` (FastAPI/SQLAlchemy/Postgres) and
  `frontend/src/app/*` (Next.js). Controlled spec baseline: `ebmr-edhr/specs/`, `ebmr-edhr/docs/generated/`,
  `ebmr-edhr/docs/adr/`.

**How to read this document:** Phase 2 (gap analysis) is organized by functional domain, in the order the
client walked through the system. Each row states current behavior (with file references), requested
behavior, and whether it's a UI fix, a backend/schema change, or a new capability. Phase 3 (implementation
phases) groups the gaps into eight dependency-ordered, independently reviewable phases. Nothing in Phase 3
should be started without your sign-off per phase, per the workflow you specified.

---

## PHASE 0 — Decision Gate (blocking, no code) — **RESOLVED 2026-10-05**

**Decision:** one eBMR deployment per client company. ADR-0006 (single-tenant-per-deployment) stays as-is — no
new ADR, no `tenant_id`, no schema change. "Admin"/"tenant" in the client's description means a distinct
client gets a distinct running instance, not a shared multi-tenant platform. This unblocks every phase below
to be scoped against the current architecture as written.

### 0.1 Tenancy model — must be resolved before Phase 1 can be scoped

| | |
|---|---|
| **Current behavior** | `ADR-0006-tenancy-model.md` (accepted 2026-08-22): single-tenant-per-deployment. One `iam.Organization` row per running instance. `assert_single_organization()` in `app/core/db.py` **raises at boot** if a second org row ever appears. No `tenant_id` column exists anywhere in the schema (confirmed absent from every module, by design). `frontend/src/app/admin/company/page.tsx` is literally subtitled "This deployment's single company record" — there is no "add company" action anywhere in the UI. |
| **Requested behavior (as described)** | Transcript (`oct-1`, lines 1–20): client describes "Admin" as a new client company logging in, with the explicit statement that "**there will be different clients... in that way there will be different Admins in our system**" and calls this "**a type of tenant**." Later (`oct-2`, lines 59–71) the client separately requires that CodeLab (the vendor) has **zero access to a client's data** once that client's onboarding is complete — "ખાલી ઓનબોર્ડિંગ વખતે આપણે એને હેલ્પ કરવાની હોય... એઝ એ કોડલેબ પાસે કોઈ જ ડેટાનો એક્સેસ નહીં હોય" (as CodeLab, there will be no data access at all). |
| **Reading this carefully** | Both requirements are satisfiable **without changing the architecture** if "tenant" here means "each client gets their own separate deployment" (vendor loses access because it's a different running instance/database, not because of in-app permission scoping). They are **not** satisfiable without a major rewrite if "tenant" means "one shared platform, many client companies, data isolated by row." The transcript does not disambiguate this — the word "ટેનન્ટ" is used loosely by a non-technical speaker describing a business concept, not a technical spec. |
| **Classification** | **SPEC_GAP — architecture/record-authority decision (AG-05, AG-03).** Not something to guess. |
| **Recommendation** | Confirm with the client: "one eBMR instance per client company" (matches current ADR-0006, zero architecture change, satisfies the stated vendor-access-revocation requirement literally) vs. "one shared platform serving multiple client companies" (requires a new ADR superseding ADR-0006, a `tenant_id` backfill migration across every regulated table, Postgres RLS, and reworking IAM/Signature/Audit/Vault to be tenant-scoped — multi-month effort touching nearly every module). Everything else in this plan (bulk onboarding, role templates, access review) is written assuming the **single-tenant-per-deployment** interpretation, since it is both the lower-risk default and consistent with the accepted ADR. If the client means the second interpretation, Phase 1 below needs to be re-scoped entirely before any of it is built. |

---

## PHASE 2 — Gap Analysis by Domain

*(Assumes the Phase 0 tenancy question resolves to "single-tenant-per-deployment," i.e., no change to ADR-0006.)*

### 2.1 Company / Site Setup

| Item | Current | Requested | Type |
|---|---|---|---|
| Company setup (name, logo, address) | `admin/company/page.tsx` — single edit-name form only. No logo, no address fields. `Organization` model (`iam/models.py`) has only `id`, `name`, `created_at`. | Logo upload, name, address, site-head/operational-head fields on the company record. | **New fields/schema** (small) |
| Multiple Sites per company | Fully supported — `Site` model (`iam/sites`), CRUD UI at `admin/sites/page.tsx`. | Matches. | None |
| One Site Head / Operational Head per site | `Site` model has no "head" field; this would currently be modeled only via a `UserSiteRole` with a "Site Head" role, with no DB constraint limiting it to one person. | Client wants exactly one person per site in that capacity. | **Validation rule** (small) — enforce uniqueness of a designated "Site Head" role per site, or add an explicit `site_head_user_id` FK on `Site`. |

### 2.2 Users, Roles, Permissions, Bulk Onboarding

| Item | Current | Requested | Type |
|---|---|---|---|
| Role model | `Role`, `Permission`, `RolePermission`, `UserSiteRole` (time-bounded, approvable, per-site) — solid foundation (`iam/models.py`). Ad hoc custom roles (e.g., "Calibration Technician") are already creatable one at a time via `admin/roles/page.tsx`. | Matches current capability already. | None |
| Module-wise permission grouping | `Permission.resource_type` exists as a column but there's no UI concept of "module" grouping — `admin/roles/[id]/page.tsx` presumably lists permissions flat or by whatever grouping exists today (not fully inspected). | Client wants a module-wise permission checklist UI for assigning roles (confirmed already partly working in the client's walkthrough — this looks like mostly a UX confirmation, not a gap). | **Verify/polish**, likely low-risk |
| **Bulk user import (CSV/Excel)** | **Does not exist at all.** No command, no endpoint, no UI. Every user, role, and site assignment is created one row at a time via `admin/users/page.tsx` modal forms (confirmed — grep for `csv\|excel\|bulk\|import` across `iam/{router,service,commands}.py` returns nothing). | Client's central onboarding ask: a pre-built Excel template (name, email, role, site/access) that gets uploaded once at go-live for ~100+ users, instead of one-by-one creation. Vendor does the first import; client self-serves afterward via an access-review step. | **New capability** — backend bulk-import command + validation/preview + commit, frontend upload+mapping UI. |
| **Master "Activity / Sub-Activity" checklist → role templates** | No equivalent exists. Permissions are assigned per-role from the flat `Permission` catalogue; there's no pre-built "feature checklist" (AI Governance, Aseptic Operation, etc.) that a client ticks to auto-generate a role's permission set. | Client wants a master catalogue of Activities/Sub-Activities that, when selected during onboarding, auto-populates the relevant permission checkboxes for a new role — this is explicitly meant to avoid the client having to understand the full permission matrix from scratch. | **New capability** — a "role template" layer on top of the existing `Role`/`Permission` schema. |
| Access Review step | `admin/access-review/page.tsx` exists already (not inspected in depth). | Client wants this as the final onboarding gate: after bulk import, client reviews/confirms the imported user/role list. | **Verify fits**, likely small wiring work to connect it to the new bulk-import flow. |

### 2.3 Process Flow / UX Sequencing (cross-cutting)

| Item | Current | Requested | Type |
|---|---|---|---|
| Logical step sequence across modules | Every module (Company, Sites, Users, Suppliers, Materials, Equipment, ...) is a separate flat page reachable via normal nav — no enforced order. | Client repeatedly asks for an end-to-end guided sequence (Company → Site → Users → Supplier → Material → Equipment → Product → Recipe → Batch), especially for first-time setup. | **New capability** — an onboarding wizard/stepper shell. Does not require changing the underlying CRUD pages, just a guided shell that links them in order with progress state. |
| Screen/window proliferation | Material and Material Specification are separate pages/tables (`materials/page.tsx`, `material-specifications/page.tsx`) backed by genuinely separate backend tables (`Material` master vs. versioned `MaterialSpecificationVersion`). Material Receipt and Examine are two distinct steps in the receipt workflow. | Client explicitly asked, twice, to **merge** these pairs of screens so data entry feels like one continuous flow, not cross-module hopping. | **UI consolidation** — can be done as a presentation-layer merge (one page, two API calls) without necessarily merging the backend tables (see 2.4 for why the backend separation is actually correct and shouldn't be collapsed). |

### 2.4 Supplier Module

| Item | Current | Requested | Type |
|---|---|---|---|
| Supplier + Site + Qualification model | Fully implemented: `Supplier` (org-wide identity), `SupplierSite`, `SupplierQualification` (risk_class, scope JSONB, status, `justification` field), `SupplierQualificationEvidence` (reuses the generic Vault for document storage). | Matches closely. | None |
| SoD on approval (creator ≠ approver) | **Confirmed enforced in code**, not just policy: `supplier_quality/commands.py` compares `actor_user_id == qualification.requested_by_user_id` and raises if equal. Client's live test of this in the walkthrough (`oct-3`) passed. | Matches exactly what was demonstrated and approved live. | None — already correct |
| "Scope" as structured material mapping | `SupplierQualification.scope` is a free-form JSONB label/value pair today ("Row material supply," "Excipient only" as free text). | Client wants Scope to map directly to a structured Material Code/Material Name via an "Add Material" button, not free text. | **Schema + UI change** (medium) — introduce a `SupplierQualificationScopeItem` join table referencing `Material`. |
| Approval field wording | Field is literally named/labeled "Justification" in the UI (matches `SupplierQualification.justification` column). | Client wants this relabeled "Explanation" for routine approvals (reserving "Justification" for exception/deviation cases). | **Label-only change** (trivial), though note the column name `justification` is shared platform convention — recommend relabeling at the UI layer only, not renaming the DB column (consistency with other modules' similarly-named reason fields). |
| Document upload / visibility in approval view | Documents are stored via the generic Vault (`SupplierQualificationEvidence` → `vault.gxp_vault_object`) with a free-text `evidence_category` (no enumerated type like "ISO Certificate" vs. "Audit Report"). Inline same-window preview on the approval screen not confirmed either way (not inspected at component level). | Client wants: (a) a true "Add Document" affordance with a name (e.g., "ISO 9001 Certificate"), effective date, expiry date, multiple docs; (b) all uploaded docs visible/openable in the same popup when an approver reviews the supplier, not hidden behind extra navigation. | **UI verification + small schema addition** — add `document_name`/`expiry_date` as first-class fields (currently only generic evidence_category + Vault object), plus confirm/build inline preview in the approval modal. |
| Minimum-certification gating by risk class (e.g., "High-risk material requires supplier to hold ISO 9001 minimum") | No such rule engine exists. | Client floated this as a policy idea during the walkthrough but did not commit to it as a hard system rule — stated as an example, not a confirmed requirement. | **Open question** — flag for client confirmation before building; likely out of scope for the first phase either way. |

### 2.5 Material / Material Specification

| Item | Current | Requested | Type |
|---|---|---|---|
| "Business ID" field | Not present on `Material` today (code field serves that role) — confirmed absent. | Client asked to remove a "Business ID" field they saw in the demo build as confusing — likely refers to `material_spec_business_id` on `MaterialSpecificationVersion`, which **is** present and user-facing. | **Field removal** (small) — remove from UI, confirm backend can use internal PK without a user-visible business ID, or replace with the material's existing human-readable `code`. |
| Material ↔ Material Specification relationship | **Deliberately separate backend tables**: `Material` (master, mutable fields like status/storage condition) vs. `MaterialSpecificationVersion` (versioned, draft→signature→release lifecycle, immutable once released). This separation exists *because* specs need independent version history and signatures distinct from the mutable master record — collapsing them at the database level would break the release/versioning model (and the regulated-record-immutability requirement, AG-08). | Client wants Material and Material Specification to *feel* like one screen/entity during data entry. | **UI consolidation only** — present as one page/flow (create material → immediately add its first spec version in the same screen), while keeping the two backend tables and their distinct lifecycles intact. This is a UX merge, not a schema merge. |
| Specification structure (Test Name / Specification / Acceptance Criteria rows) | `MaterialSpecificationVersion.acceptance_criteria` is **a single unstructured JSONB blob** — explicit code comment confirms "no acceptance-range execution/evaluation engine exists yet... stores declared criteria without interpreting or enforcing them." | Client wants a proper repeatable table: Test Name / Specification / Acceptance Criteria columns, add-as-many-as-needed, each row carrying its own test-method-type (In-House / External Lab / Supplier-COA) selection. | **New schema** (medium-large) — a `MaterialSpecificationCriterion` child table replacing the JSONB blob, each row with `test_name`, `specification_text`, `acceptance_criteria`, and `fulfillment_path` enum. This also unblocks the three-pathway testing logic in 2.6. |
| Document-based spec auto-extraction | Does not exist anywhere (grep for `extract\|ocr\|parse_document\|ai_` in the material-specification module returns nothing; a separate unrelated `ai_governance` module exists but isn't wired in). | Client wants: upload a company's existing spec PDF/document → system auto-reads it and proposes Test Name/Specification/Acceptance-Criteria rows → user reviews and accepts each row one-by-one before it's saved. Explicitly driven by scale (2,000–3,000 materials × up to 50 specs each — manual entry is impractical). | **New capability, AI-advisory only (AG-14 compliant)** — a document-parsing suggestion engine that proposes rows into the new `MaterialSpecificationCriterion` table from 2.5 above; nothing is committed without the human accept-per-row step the client themselves specified, which is exactly what AG-14 requires anyway. |
| Material status (Active/Inactive) | `Material.status` field exists (default `active`), confirmed present. | Client was unsure during the walkthrough what this status actually represents and asked to leave it as-is pending his own review — **not currently a confirmed request to change**. | **No action** — client explicitly deferred this to himself ("I'll review it, leave as-is for now"). |
| Material "Type" (Raw Material / Consumable / Chemical) | No `type`/classification field exists on `Material` today. | Client raised this but explicitly deferred it to his own to-do list ("not now, I'll think about it"). | **Deferred by client** — do not build without a follow-up confirmation. |
| Lot Number on Material master | Correctly absent — lot numbers are (correctly) only assigned later, at Material Receipt. | No change requested; client confirmed this is correct as-is. | None |

### 2.6 Material Receipt / Incoming Examine / QC Testing

| Item | Current | Requested | Type |
|---|---|---|---|
| Receipt + Examine as separate screens | Two distinct steps in the workflow today (confirmed: `MaterialReceipt` model includes COA/discrepancy-hold fields; a separate "examine" interaction layer sits on top). | Client explicitly, repeatedly asked to merge these into one sequential screen — called out twice as "a module shouldn't be crossed; merge it into one." | **UI consolidation** (frontend-only, same pattern as 2.3). |
| "Identity Confirmed" field naming | Present as a field in the examine step (exact current label not fully inspected, but conceptually present per `MaterialReceipt`/examine fields). | Client flagged "Identity" as a pharma term-of-art meaning a *chemical test*, not a label check — field should be renamed to something like "Material Matched with PO and Material Number." | **Label/field rename** (trivial). |
| Damage / Contamination / Seal checks | Current examine step appears to have a single generic "Damage Observed" concept (exact current shape not fully inspected at field level). | Client wants: split into "Shipping/Package Damage" vs. "Material Container Damage" (two distinct checks); drop "Contamination Observed" entirely (explicit descope); rename "Seal Broken" to "Seal Intact?" (Yes/No, with "No" triggering free text). Each Yes/No field needs an "unintended answer triggers free-text comment" pattern (e.g., Damage=Yes, Labeling Correct=No). | **Field restructuring** (small-medium) — mostly form-schema changes plus consistent conditional-free-text UI pattern. |
| Container-count splitting for bulk receipts | Not confirmed present (e.g., 100kg received as 4×25kg containers, each labeled "n of 4"). | Client wants this, but **explicitly deferred barcode/label generation** to a later phase — "we'll take it later." | **Deferred** — only the container-count data model needs scoping now; labeling/barcode generation is out of scope for this round. |
| Quantity fields (Ordered/Received/Accepted, PO reference) | `MaterialReceipt` has quantity and COA fields; "PO Reference" appears to be a free-text field today with **no actual Purchase Order module** behind it to pull Ordered Quantity from. | Client wants PO Reference to eventually resolve against a real PO record (Ordered Quantity auto-populated, partial-order detection), but acknowledged **no PO/procurement module currently exists** to back this — flagged as a dependency, not actioned this round. | **Deferred / dependency flag** — a full Purchase Order module is out of scope for this phase unless the client confirms they want it prioritized. |
| Three testing fulfillment paths (In-House / External Lab / Supplier-COA reliance) | Not modeled today — `MaterialSpecificationVersion`'s single JSONB blob has no per-test fulfillment-path concept, and the QC/testing modules referenced by the client ("a newer version is in separate development with many changes") are **not inspected in this pass** and are explicitly called out by the client as work-in-progress elsewhere. | Client wants each spec test to carry a fulfillment-path selection made at spec-definition time (2.5), which then drives the Material Receipt testing flow: In-House (test method reference + result), External Lab (send-to-lab → upload report → result, lab must be an "Approved Service Provider"), or COA-reliance (auto-build a Certificate of Conformance from supplier's COA data, user just types in results). | **New capability, dependent on 2.5's structured spec table and 2.6's "Global QC Testing module" (see below).** |
| "Service Provider" concept (Supplier extended to Goods and/or Services) | `Supplier.role_type` enum is `supplier \| manufacturer \| both` today — **no "service" type exists**; calibration vendors, repair vendors, and test labs have no home in the current Supplier model. | Client wants Supplier extended so a "Service Provider" (calibration company, repair vendor, external test lab) is just another Supplier record, reusable as a dropdown source in Equipment Calibration's "Provider Name" field and Material's External Lab testing path — instead of free text. | **Schema change** (medium) — extend `role_type` enum or add a `service_categories` field, and change Equipment Calibration's `provider_name` (currently free text) to a FK into Supplier. |
| **Global QC Testing / Result module** | **[CORRECTED] Already exists and is substantially built**, at `app/modules/qc/` (Document 23/SPEC-QC-001 + Document 25 OOS/OOT): `QcTestSpecification` (scope_type already covers `product` / `in_process` / `device` / `material` — this **is** the client's "three test categories," plus a device category), `QcMethodVersion` (`method_type` = compendial/internal/validated, with a `validation_evidence_reference` field — exactly the Compendial/Validated distinction the client described), `QcTestDefinition` → `QcSample` → `QcTestOrder` → `QcTestRun` → `QcResult` (full draft→in-progress→reviewed→outcome lifecycle, append-only/immutable per AG-08), plus `OosRecord`/`OotRecord`/`OosInvestigationActivity`/`QcResultCorrection`. A generic acceptance/arithmetic **rule engine** (`rules.gxp_rule_definition`, referenced via `QcTestDefinition.acceptance_rule_business_id` and `QcTestRun.calculation_rule_object_id`) already exists — this is the "complex calculation... 5 years away" capability the client assumed was future work. **Confirmed real integration**, not just schema: `material/commands.py` already creates a `QcSample` on material receipt and blocks lot release until required/release-blocking `QcTestDefinition`s have a passing `QcResult` (exact mechanism the client asked for). **The actual gap:** `QcTestRun.instrument_ref` is an explicit, documented unwired placeholder — its own code comment says "no equipment/instrument entity exists," which was true when that comment was written but is now stale (Equipment/WP-06 has since been built elsewhere and this reference was never backfilled). Equipment Calibration today keeps its own separate result/pass-fail fields on `EquipmentCalibration` rather than routing through `qc`. | Client's ask (one shared engine, reused by Material + Equipment + future Batch testing) is **already true for Material**; the only missing link is wiring Equipment Calibration into the same `qc` pipeline instead of its parallel fields. | **Integration work, not new-module work** — much smaller than originally scoped. The client's live reference to "a newer QC Testing version in separate development" may well be this very module (it predates the Oct 3/4 recording, built in a session on 2026-09-21) — worth confirming directly with the client whether this is in fact what they meant, since it would mean much of their "future work" concern is already resolved. |
| Pass/Fail vs. Approved/Not-Approved | Not confirmed as two distinct fields everywhere yet (varies by module — `EquipmentCalibration.result` is `pass\|fail\|oot`, separate from any QA-approval field). | Client explicitly wants these kept conceptually and structurally separate everywhere: Pass/Fail = objective result-vs-acceptance-criteria outcome; Approved/Not-Approved = subjective QA/Releaser disposition. | **Consistency check** across whichever module(s) the Global QC Testing module (above) ends up touching. |
| Sampling Quantity | `qc.QcSample.sample_quantity`/`sample_uom` already exist as free-entry fields, but there's no rule defining what the *required* sampling quantity should be per test/material, decided at spec-definition time. | Client wants this decided at the same moment as the per-test fulfillment-path selection (2.5), but **explicitly said to leave it open** — "I don't have an answer right now, I need to think about this." | **Deferred by client** — do not build a sampling-quantity rule without a follow-up confirmation; the underlying field already exists for whenever this is picked up. |
| Sampling Plan / Quality Plan reference documents | `QcTestSpecification.sampling_plan` (JSONB) exists but is unstructured/unused; no document-upload concept for these two document types exists anywhere. | Client wants a lightweight "Miscellaneous Documents" tab (upload-only, no structured data entry) somewhere accessible, holding a company's master Sampling Plan and Quality Plan documents — explicitly framed as a stopgap ("I don't yet know how to properly integrate this, revisit later"), not a real module. | **Deferred by client, small when picked up** — a simple upload tab reusing the generic `evidence` module pattern (same approach already used for Equipment's Documents tab) would satisfy this with no new schema; client explicitly said not to build structured data entry for it yet. |
| Retest workflow | `qc` module already has schema for this (`OosRetestPlan`, `OosResamplePlan`, `QcTestDefinition.max_retests`) — more built than the client realizes, same pattern as the broader QC module correction above. | Client explicitly said retest is out of scope for now — "I'm not focusing on retest right now, that's a whole new subject, otherwise we'll just go in circles" — until the Material module itself is complete. | **Deferred by client** — worth telling them the schema groundwork already exists, same as the QC rule-engine finding, but do not build the retest UI/workflow without their go-ahead. |

### 2.7 Equipment / Asset Module

| Item | Current | Requested | Type |
|---|---|---|---|
| Core asset fields (manufacturer, model, serial, firmware version) | All present on `EquipmentAsset` (`equipment/models.py`), confirmed. | Matches. | None |
| Computer-system vs. manual-system distinction | **Confirmed absent** — no such field anywhere on `EquipmentAsset` or elsewhere in the module. | Client wants a new mandatory question at equipment creation: "computer-operated or manual?" — if computer-operated, branch into a separate Computer System Validation (21 CFR Part 11) questionnaire (audit trail presence, data recorded, etc.). Client explicitly deferred the detailed CSV questionnaire design to a follow-up. | **New field now** (`is_computer_operated` flag) **+ deferred new sub-workflow** (CSV questionnaire) pending client's detailed design. |
| New vs. Old equipment at creation | No such distinction exists today — all equipment is created the same way, moving through the same `PLANNED → INSTALLED → QUALIFICATION_PENDING → ...` state machine. | Client wants a New/Old toggle at creation: "Old" (migrating in existing equipment) skips straight to capturing existing Calibration Date/Expiry rather than going through fresh IQ/OQ/PQ/DQ. Client explicitly deferred the exact old-equipment rules pending peer consultation. | **Deferred** — flag the toggle concept now, hold detailed rules for a follow-up. |
| Equipment "eligible for use" gate | **[IMPLEMENTED, Phase 4]** `_ineligibility_reasons()` now has a `CALIBRATION_APPROVAL_PENDING` reason: a passing calibration alone no longer clears eligibility — it must also be approved by someone independent of the performer. Built as a direct extension of `EquipmentCalibration` (new `approved`/`approved_by_user_id`/`approved_at` columns + a second SoD-checked call to the same `record_calibration` endpoint), **not** by wiring through the `qc` module's pipeline — that approach was scoped out as a UX regression once `qc`'s actual multi-step commands were read (see Phase 4 in §3 below for the full correction). | Client wants an **additional** gate: equipment must also clear a QC/QA sign-off step before being eligible for use, not just Qualification. | **Done** — same `_ineligibility_reasons()`/error-code-map pattern already used for every other equipment gate, just a new reason code, not a new architecture. |
| Calibration field order & Provider Name sourcing | `EquipmentCalibration` has `calibration_type` (internal/external), `provider_name` (**free text**), `standard_reference`, `result`, performer/reviewer split (SoD-ready) — fields exist but not necessarily in the client's requested display order, and `provider_name` is not yet FK'd to Supplier. | Client wants a specific field sequence (Performance Date → Internal/External → SOP/Standard Reference or Provider+Certificate → Result sub-table → Pass/Fail → Approved/Not-Approved → Next-Due-Date-as-interval-or-date-at-approval-time-only) and wants `provider_name` to be a dropdown sourced from Approved Suppliers/Service Providers (2.6), and ultimately wants this whole form to become a thin wrapper around the Global QC Testing module. | **UI resequencing (small) + FK change (small) + eventual integration with 2.6 (depends on that module existing).** |
| Maintenance: Plan / Corrective / Breakdown | `MaintenanceWorkOrder.type` already supports `planned\|corrective\|breakdown`, with separate technician/verifier fields (SoD-ready). | Matches the three-type model. | None |
| Breakdown → mandatory recalibration gate (unless non-critical) | No "recalibration required" flag or critical/non-critical breakdown distinction exists on `MaintenanceWorkOrder` today. | Client wants: any breakdown maintenance defaults to requiring recalibration before the equipment can be used again, *unless* flagged non-critical (example given: a mere power-supply failure). Client explicitly deferred the detailed critical/non-critical rule design. | **New field now** (`recalibration_required` Yes/No + resulting use-block, matching 2.6's "eligible for use" gate) **+ deferred detailed criticality rules.** |
| Maintenance activity checklist | `MaintenanceWorkOrder` has free-text `work_performed`/`diagnosis` fields but no repeatable Activity/Result sub-table. | Client wants a two-column repeatable table (Activity, Result/Outcome) for Plan maintenance, mirroring a car-service-style checklist. | **New schema** (small-medium) — a `MaintenanceActivity` child table. |
| Maintenance specification + acceptance criteria | Does not exist. | Client raised this but explicitly deferred the entire design ("I haven't reviewed this in detail — hold it, I'll send you a proper design later"). | **Deferred by client** — do not build without a follow-up design doc from the client. |
| Bulk equipment import (Excel) | Does not exist (same gap as bulk user import, 2.2). | Same ask as users: a pre-built Excel template for ~500 existing equipment items at go-live, uploaded once; historical calibration/maintenance entered manually afterward per item. | **New capability** — reuses the same bulk-import framework built in Phase 1 for users, applied to Equipment. |
| Equipment document upload | **[CORRECTED] Already solved, no gap.** A 2026-09-21 session added an Equipment "Documents" tab by reusing the generic `evidence` module (`EvidenceObject.owner_type`/`owner_id` — a free-string polymorphic pattern already used elsewhere) rather than adding a 5th equipment-specific table. This correctly preserves the controlled spec's 4-entity freeze (`EquipmentAsset`, `EquipmentCalibration`, `MaintenanceWorkOrder`, `EquipmentUseLog`) while still giving Equipment real document upload (qualification docs, calibration certs, maintenance notes), confirmed present in the current codebase. | Client wants document upload throughout the equipment workflow. | **No action needed** — already matches the request. |

### 2.8 Product Master (meeting ran out of time — partial only)

| Item | Current | Requested | Type |
|---|---|---|---|
| Duplicate name fields | Not independently verified this pass — client referenced seeing both a "Brand Name" and a separate "Product Name" field. | Merge into a single "Product Name" field. | **Field consolidation** (small, pending verification) |
| "Business ID" field | Same pattern as Material/Supplier. | Remove, consistent with the rest of the simplification requests. | **Field removal** (trivial, pending verification) |
| "Manufacturing Profile" section | Client flagged this as a vendor-internal construct not meant for client-facing use, but also flagged that "many things are performed off Manufacturing Profile internally" — i.e., hidden dependencies are suspected. | Hide from the client-facing Product Master screen without deleting the underlying data/field, pending a dependency investigation. | **UI-only hide, deferred backend investigation** — do **not** delete anything here without first tracing what currently reads `Manufacturing Profile`. |
| Category-specific fields (device vs. pharma vs. injectable) | Not inspected this pass. | Product form should branch by product category, showing device-specific fields (e.g., Stent Length/Diameter) only for device products. | **New capability** — needs its own exploration pass once this phase is reached; the client meeting was cut short here and will likely continue in a future session. |
| **Bulk import (Excel)** | Not inspected this pass; given the same gap exists for Users (2.2) and Equipment (2.7), Product Master almost certainly has no bulk-import capability either. | Client explicitly confirmed this (`eBMR-04-oct-2.txt`): asked directly "like we give an Excel-sheet option for Users, should we give one for Product too?" — answered "Yes yes, we'll give it." Same first-time-onboarding pattern as Users/Equipment. | **New capability** — reuses the bulk-import framework built in Phase 1, applied to Product Master. |

### 2.9 Field Labeling, Ordering & Recurring UI Conventions (cross-cutting)

These are individually small — a renamed label, a reordered field, a formatting convention — but they're scattered
across nearly every screen discussed in the transcript. Listing them together here so none get lost inside the
larger architectural rows above (several of these were missed in an earlier pass of this document for exactly
that reason).

| Item | Where | Current | Requested |
|---|---|---|---|
| "Examination Notes" → "Shipment Examination Notes" | Material Receipt/Examine (2.6) | Generic "Examination Notes" label | Rename for clarity once the Receipt+Examine screens are merged |
| "Standard Reference" → "Standard/Traceable Reference" | Equipment Calibration (2.7) | `EquipmentCalibration.standard_reference`, labeled "Standard Reference" | Relabel to "Standard/Traceable Reference" |
| Capital "P" in "Pass" | Equipment Calibration + Material/QC results (2.6, 2.7) | Not confirmed enforced | Client explicitly asked for consistent capitalization of the literal value "Pass" — a data/display convention, not a new field |
| "Not Applicable" toggle instead of blank-means-N/A | Equipment (Firmware Version), Material Receipt (Supplier/Manufacturer Lot Number) | Free-text fields; blank isn't distinguished from "genuinely not applicable" | A checkbox/button defaulting to "Not Applicable" when a field doesn't apply, instead of relying on a blank value to mean the same thing |
| "(Optional)" suffix on optional field labels | Material Receipt (Retest Date), likely other optional fields | Asterisk convention marks required fields; optional fields aren't explicitly labeled as such | Add "(Optional)" next to optional field labels, paired with the "Not Applicable" toggle above where relevant |
| Capitalize-first-letter / proper-case convention | Recurring across many screens (placeholder text, dropdown values, free-text entries made live during the walkthrough) | Inconsistent | Client repeatedly asked for proper-case defaults — a UI polish pass, not a functional change |
| Product Master field order | Product Master (2.8) | Not inspected this pass | Client wants a specific column order: Product Family (first) → Product Code → Product Name → Strength/Dose |

**Classification:** all trivial-to-small, UI-only, no schema or workflow impact. Recommend bundling each into
whichever phase already touches that screen (noted inline in Phase 3's phase descriptions below) rather than a
dedicated phase.

---

## PHASE 3 — Implementation Phases

Each phase below is scoped to be independently reviewable and shippable. Dependencies are called out explicitly.
**No phase should be started without your explicit go-ahead**, per the workflow you specified — this section exists
so we can discuss each phase's shape before any of it becomes a plan to implement.

### Phase 1 — Bulk Onboarding Foundation (Users) — **IMPLEMENTED 2026-10-05**
- **Objective:** Let a new client (or CodeLab on their behalf) upload a spreadsheet of users (name, email, role, site) once at go-live instead of one-by-one creation.
- **What shipped, concretely:** per-user password-setting was replaced with an email-invite flow (the
  client's actual stated design — "whoever's email is entered gets invited and signs up themselves" —
  which `create_user`'s existing admin-sets-password contract couldn't satisfy, so this became a new
  `invite_user`/`accept_invite` pair alongside, not instead of, `create_user`). stdlib `smtplib` only — no
  new dependency, no Document 104 process triggered. Migration `0132_user_invites` (table `iam.user_invites`,
  additive, applied + verified via forward/rollback cycle on both the live and test databases, including
  the runtime-role GRANT). Backend: `POST /users/invite` (single-row), `POST /users/bulk-import/preview`
  (validate-only), `POST /users/bulk-import/commit` (all-or-nothing), `POST /auth/accept-invite` (public,
  single-use/expiring token). Frontend: a "Bulk import" button + CSV-paste modal on `/admin/users`, and a
  new public `/accept-invite` page. 8 new automated tests, all passing; full existing suite re-run clean.
  Verified against the live running deployment via real HTTP (not just the test DB): preview flags bad
  rows, commit creates `pending_activation` users who cannot log in, accept-invite activates them
  (bad/expired/reused tokens correctly rejected), and login then succeeds — see session notes for the
  exact curl transcript. Test accounts created during this verification were deactivated afterward.
- **Deliberately not done:** Excel (.xlsx) parsing — CSV only, to avoid a new parsing dependency on either
  side; the admin exports/saves their spreadsheet as CSV first. The exact column template
  (`full_name,email,role_name,site_code`) was chosen rather than separately re-confirmed with the client —
  flag for their review once they see the actual UI.
- **Client requirements covered:** 2.2 (bulk user import), partially 2.2's access-review wiring.
- **Backend:** new `bulk_import_users` command in `iam` module — parse/validate rows, dry-run preview with row-level errors, commit creates `User` + `UserSiteRole` rows per existing single-row commands (reuses them, doesn't bypass validation).
- **Frontend:** file-upload + column-mapping + preview/error screen in `admin/users/`, wired to the existing `admin/access-review/page.tsx` as the final confirmation step.
- **DB/API:** no schema change required (reuses existing `User`/`Role`/`UserSiteRole` tables); new endpoint(s) only.
- **Dependencies:** none — can start immediately once Phase 0 resolves.
- **Open questions:** exact spreadsheet column set/template format — needs a client-approved template before building the parser.

### Phase 2 — Role/Permission UX: Activity Catalogue & Role Templates — **IMPLEMENTED 2026-10-05**
- **Objective:** Let an admin pick from a master "Activity/Sub-Activity" checklist to auto-populate a new role's permissions, instead of manually ticking the full permission matrix.
- **Client requirements covered:** 2.2 (activity catalogue → role templates).
- **Design correction before build:** the existing `admin/roles/[id]/page.tsx` matrix was already better
  than this doc assumed — it already groups all (then-457) permissions into ~128 collapsible technical
  "module" groups (parsed from the `<module>.<resource>.<action>` code prefix), with per-group select-all
  and search. The real gap was that 128 technical module names is still too many/jargon-y for a
  non-technical admin, not "there's no grouping at all." So the Sub-Activity tier reuses those existing
  128 module keys as-is — no new technical taxonomy was invented.
- **What shipped, concretely (Option A from two user-approved decisions — frontend-only catalogue,
  add/merge selection semantics):** a static, vendor-maintained `ACTIVITY_CATALOGUE` table in
  `frontend/src/lib/activityCatalogue.ts` bundling the 128 module keys into 15 business-named Activities
  (Material Management, Suppliers, Equipment & Facilities, QC Testing & Lab, Quality Events, Product &
  Recipe Master, Batch Execution / eDHR, DDCP, Documents & Training, Postmarket & Vigilance, Enterprise
  Integrations, Security & Access Governance, Audit & Vault, AI Governance, Platform Operations &
  Reporting), verified to cover all 128 real module keys exactly once (no typos, no duplicates, no gaps)
  by diffing against the live `PERMISSION_CATALOG` in `scripts/seed.py`. A new "Activity checklist" panel
  in `admin/roles/[id]/page.tsx` renders one checkbox per Activity; ticking one adds (merges) its
  permissions into the existing `selectedIds` state and auto-expands the matching module groups below for
  visibility, reusing the page's existing `toggleModule`/`moduleState` helpers rather than new logic;
  unticking removes just that Activity's permissions. The full technical matrix stays visible underneath
  for fine-tuning before Save. **Zero backend change**: no new table, no migration, no new endpoint, no
  SPEC_GAP — the unchanged `GET /permissions` + `POST /roles/{id}/permissions` (`set_role_permissions`)
  mutation path is the only thing that ever gets called on Save. A dynamic "Other" bucket covers any
  future `PERMISSION_CATALOG` module key not yet filed under a named Activity, so new permissions can
  never become untickable through this checklist.
- **Verified against the LIVE running deployment** (pm2 `ebmr-new-api`/`ebmr-new-frontend` under the
  `frappe` user) via a real Playwright browser session (ad hoc, installed to the session scratchpad only
  — not added to `frontend/package.json`/the project's dependency set): logged in as `admin`, created a
  throwaway role, ticked "AI Governance" (confirmed exactly its 13 permissions got selected and its module
  group auto-expanded), ticked "Equipment & Facilities" on top (confirmed the count grew — merge, not
  replace), unticked "AI Governance" (confirmed only its permissions were removed), saved, reloaded the
  role and confirmed the selection persisted exactly and the Equipment & Facilities checkbox read back as
  fully checked. All assertions passed. The throwaway role was deleted via the API afterward, leaving no
  residue. `npx tsc --noEmit` and `npx eslint` both clean on the two changed files.
- **Deliberately not done:** no client-editable catalogue (seed-only/vendor-maintained, per the user's
  explicit choice between the two options presented); no new backend "apply template" command (the
  frontend resolves Activity → permission-id sets client-side and still calls the existing, unchanged
  `set_role_permissions` endpoint directly — smaller footprint than this doc originally sketched, since
  the admin already has the full permission list loaded for the existing matrix).
- **Open question resolved:** "who maintains the Activity Catalogue" — vendor-only static config for V1,
  per the user's explicit pick; revisit as a separate future phase if client-side editing is ever wanted.

### Phase 3 — Supplier UX Refinements — **IMPLEMENTED 2026-10-05**
- **Objective:** Make Supplier qualification scope structured (material-mapped, not free text), fix approval wording, and confirm/build inline document preview.
- **Client requirements covered:** 2.4 in full (minimum-certification-by-risk-class gating stays explicitly out of scope — never confirmed by the client, per the original open question).
- **Design correction before build:** the evidence side of this phase was reframed after inspecting the
  actual code. `SupplierQualificationEvidence` joined to `vault.gxp_vault_object`, but Vault's only
  endpoint is a full signed master-record release ceremony (`POST /vault/v1/masters/{type}/{businessId}/
  release`) — there was never a real upload UI, only a raw "paste a vault_object_id you have no way to
  obtain" text field. The Equipment module already solved exactly this problem on 2026-09-21 by reusing
  the generic `evidence` module (`POST /evidence/v1/uploads` → `:finalize`, polymorphic
  `owner_type`/`owner_id`, free-form `provenance` JSONB) instead of Vault. This phase reuses that same
  proven pattern for supplier qualifications rather than adding `document_name`/`expiry_date` columns to
  the Vault-backed join table as originally sketched — **zero backend change** for documents at all; the
  upload/list/download endpoints already existed.
- **What shipped, concretely:**
  - **Structured scope** (schema change): new additive table `ebmr.supplier_qualification_scope_item`
    (migration `b4d6f8a0c2e4`/`0133`, FK to `ebmr.supplier_qualification.id` and `materials.materials.id`,
    unique on the pair) — also satisfies the MAT-003 "Approved Supplier List" material-to-approved-
    supplier relationship named in the architecture rules extract, not a bespoke UI-only table.
    `CreateSupplierQualificationCommand` gained `scope_material_ids: list[uuid]` (validated, same command/
    transaction, no new endpoint); `_qualification_dict()` now also returns `scope_items` with the
    material's code/name resolved. Per the user's explicit choice, the free-text `scope` JSONB field was
    **kept alongside** the new structured list (not replaced) for notes that don't map to a material.
    Frontend: an "Add Material" picker (reusing `useEntityOptions().materials`, already loaded elsewhere)
    replaces the old free-text `KeyValueRows` as the primary scope control in the Request Qualification
    modal; the qualification table shows the scoped materials' codes.
  - **Documents** (no backend change): a new "Documents" button per qualification row opens a modal
    listing/uploading evidence via the generic `evidence` module (`owner_type="supplier_qualification"`),
    with a real "Add Document" form (document name, category, effective/expiry dates, file) — all
    visible/openable in the same popup an approver reviews the qualification from. The old raw-vault-
    object-id "Supporting evidence" field was dropped from the create-qualification modal (never had a
    real upload UI anyway) in favor of adding documents after creation, matching Equipment's own flow.
    The original `SupplierQualificationEvidence`/Vault join table and its `evidence` creation-time field
    are left untouched for backward compatibility — this is a second, additive path, not a replacement.
  - **"Justification" → "Explanation"** (label-only): the approval modal shows "Explanation" (optional)
    when `decision === "approved"`, "Justification" (required) for `conditional`/`rejected` — exactly the
    client's ask. No backend/column change.
- **Backend tests:** `tests/test_supplier_quality.py` — 2 new tests (`scope_material_ids` attaches +
  round-trips with code/name, unknown material id rejected with `NOT_FOUND`); 17/17 passing. Found and
  fixed two real pre-existing bugs while writing these: (1) a transaction-ordering bug in the new test
  itself (a `SELECT` before an explicit `db.begin()` autobegins a transaction that then conflicts with it
  — fixed by reordering, matching an existing test's precedent); (2) `tests/conftest.py`'s independently
  duplicated permission catalogue was missing `supplier.view` entirely (present in `scripts/seed.py` and
  already granted there to QA Releaser/Supervisor/QA Reviewer/etc. via `QMS_VIEW_CODES`) — every
  `GET /suppliers/v1*`/`GET /supplier-qualifications/*` call 403'd for every seeded test user before this
  fix. Added the missing catalogue row + granted it to `QA Releaser` only (matching production exactly,
  not a new authorization decision) — same "duplicated catalogues, update both" drift class noted in
  project memory from earlier sessions. Full existing suite re-run in the background to confirm no
  regressions (contended once with a concurrent pytest run from a peer session on the same test DB —
  flagged to that session via SendMessage, they killed the stuck backend, re-ran clean solo afterward).
- **Migration:** `b4d6f8a0c2e4_0133_supplier_qualification_scope_items` — additive only. Forward+rollback
  cycle tested on the test DB; applied to both the live `ebmr_new_gxp` and `ebmr_new_gxp_test` databases
  (migrator-role credentials sanity-checked against the live DB via `psql` first, per standing project
  guidance). Not logged in `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md` — that compiled artefact's
  own migration-number sequence is independent of (and already collides with) the real, ad hoc-incrementing
  `migrations/versions/` numbering this client-driven work uses; same traceability-scoping decision Phase 1
  made and documented (client-driven work is tracked here, not forced into the formal baseline files).
- **Verified against the LIVE running deployment** (pm2 `ebmr-new-api` restarted to pick up the backend
  change, `ebmr-new-frontend` hot-reloads under `next dev`) via a real Playwright browser session: created
  a throwaway supplier+site, added a real Material to scope via "Add Material" (confirmed it appears in
  the chosen list and the qualification table shows its code after submit), uploaded a real file via "Add
  Document" with a document name/category (confirmed it lists with the right name/category and a
  working Open/download button), and confirmed the Approve modal's label swap (Explanation for
  "approved", Justification for "rejected"). All assertions passed.
- **Known limitation / not cleaned up:** the two throwaway test suppliers created during manual/Playwright
  verification (`Claude Phase3 Verify Supplier...`) could not be removed — unlike Phase 1's test user
  accounts (which have a `deactivate` endpoint), `Supplier` has no delete/suspend endpoint reachable from
  the API (`suspend_supplier`/`reinstate_supplier` in `commands.py` are only ever called internally from
  SCAR closure, never exposed via a route) — and writing to the row directly would violate the "no
  production database fix outside a controlled migration/repair mechanism" rule. They remain in the live
  demo DB as harmless, clearly-named residual test data.
- **Deliberately not done:** the "minimum certification required by risk class" supplier-gating rule —
  client never confirmed this as a hard requirement (see the original open question); not built.

### Phase 4 — Equipment Calibration Approval Gate — **IMPLEMENTED 2026-10-05** (scope revised twice — see below)
- **Scope correction #1 (pre-implementation):** the original plan above (wire Equipment Calibration through `qc`'s `QcSample→QcTestOrder→QcTestRun→QcResult` pipeline) was found to be the wrong mechanism once `qc`'s actual commands were read in full: that pipeline is a genuinely heavy 6-step workflow (create sample → receive → create test order → start [analyst-qualification-checked] → record raw data → record result → complete → review), whereas Equipment Calibration today is one atomic `record_calibration` call. Routing calibration through it would have been a real UX regression with no concrete client ask behind it (`QcTestRun.instrument_ref` is just an unvalidated free-text field today, not something the client referenced). Corrected to: keep `record_calibration` as one call, add a second, SoD-enforced **approval** step directly on `EquipmentCalibration` — mirroring patterns already proven elsewhere in this codebase (Supplier Qualification's approver-independent-of-requester check; Maintenance's own "continue an existing record via a second call" shape).
- **Scope correction #2 (mid-implementation, user decision):** making approval a *hard eligibility gate* (equipment unusable until approved) vs. a *soft/informational* field was flagged as a genuine quality-process decision, not an implementation detail — it broke 4 existing passing tests' assumption that a passing calibration is immediately usable, and would change the live demo's calibration flow. User chose **hard gate**; the 4 tests (plus one more found via a full grep sweep, `test_return_to_service_rejected_while_dirty`) were updated to add the new approval step rather than relaxed to avoid it.
- **What shipped:** `EquipmentCalibration` gains `approved`/`approved_by_user_id`/`approved_at` (migration `0134_equipment_calibration_approval`, purely additive). `RecordCalibrationCommand` gains an optional `calibration_id` — when provided, the same endpoint reviews/approves an existing calibration instead of creating a new one (SoD-enforced: approver ≠ performer, `INVALID_TRANSITION` otherwise). New permission `equipment_asset.approve_calibration`, granted to QA Releaser and Admin (not Calibration Technician — that's the whole point). `_ineligibility_reasons()` gained a new `CALIBRATION_APPROVAL_PENDING` gate: a passing calibration lands the asset in `pending_approval` (not `current`) until a different, independent actor approves it; rejection sets `rejected`, also blocking. Only the asset's *latest* calibration can move its status — approving an older, superseded one is recorded but doesn't resurrect a stale state (tested explicitly). Frontend: the equipment detail page's Calibration tab gained an "Approved" column with inline Approve/Not-approved review (`ApproveCalibrationModal`), gated on the new permission; also fixed a GET-serializer-drops-field bug where `get_equipment_history()` never exposed the three new columns at all.
- **Tests:** 7 new (SoD rejection, role-separation rejection, reject-then-ineligible, double-approval rejection, unknown-calibration-id 404, stale-calibration-doesn't-resurrect-status, missing-result-fields validation) plus the 4+1 existing tests updated for the new gate. 95/95 passing across `test_equipment_flow.py`, `test_em_flow.py` (equipment eligibility is reused there for EM instrument checks), `test_cleaning_flow.py` (same, for line clearance), `test_dashboard_reminders.py`, plus `test_iam_admin.py`/`test_iam_bulk_import.py`/`test_policy_engine.py` as a regression check on shared `iam` code.
- **Verified against the live deployment** via real HTTP: created a test asset, qualified it, calibrated it (confirmed `pending_approval` + `CALIBRATION_APPROVAL_PENDING` ineligibility), confirmed the performer could not self-approve (SoD `INVALID_TRANSITION`), had an independent QA Releaser approve it (confirmed `current` + eligible), then retired the test asset via its normal signed ceremony to clean up (equipment has no delete, by design — audit-trail preservation, same as users in Phase 1). `scripts/sync_permissions.py` run against the live DB to pick up the new permission (1 permission created, 2 grants added).
- **Deliberately not done:** the "Provider Name → dropdown of Approved Suppliers/Service Providers" piece stays in Phase 6 (Service Provider concept) as originally scoped, not pulled into this phase.

### Phase 5 — Material & Material Specification Overhaul

**Part A — IMPLEMENTED 2026-10-05:** structured criteria rows + Business ID removal.
- **Pre-implementation findings that shaped the design:** no UI anywhere ever wrote the old `acceptance_criteria`
  JSONB field (confirmed live: the one existing released row had it `null`) — this was greenfield, not a
  format migration, so no backfill was needed. There was also no "update an existing draft" command at all
  (only one-shot create + release) — a generic "replace the whole draft" PATCH would have violated this
  project's own ban on generic CRUD/PATCH-style endpoints (CLAUDE.md §9), so the design uses specific
  `add_specification_criterion`/`update_specification_criterion`/`remove_specification_criterion` commands
  against a real child table instead.
- **What shipped:** new `MaterialSpecificationCriterion` table (migration `0135`) with `test_name`/
  `specification_text`/`acceptance_criteria_text`/`fulfillment_path` (in_house/external_lab/supplier_coa),
  draft-only mutability (enforced against the parent version's `lifecycle_state`, not a flag on the row).
  `material_spec_business_id` is no longer a caller-supplied field — it's derived deterministically from the
  material's own `code` (`f"{material.code}-SPEC"`) and hidden from the create form entirely; `version_no` is
  now optional and auto-increments when omitted (same "stop making callers hand-compute a number the system
  already knows" reasoning as Phase 4's calibration due-date computation). The old `acceptance_criteria` JSONB
  column stays in the schema, unreferenced by new code (MIG-FR-004 expand/contract — not dropped in the same
  pass that stops writing it). The release snapshot (Vault) now captures the real structured criteria rows
  instead of the always-null blob.
- **Frontend:** `NewDraftModal` rebuilt — Business ID/Version Number fields removed, a `RepeatableRows`-based
  criteria editor added (matches a Certificate of Analysis table shape, per the client's own description),
  draft creation and criteria population happen as one continuous submit rather than two navigations. Also
  added a criteria preview table to the release signature ceremony itself, so a QA Releaser can actually see
  what they're approving before signing (same "evidence visible in the same window" principle the client
  raised for supplier qualification documents).
- **Regression found and fixed:** removing the `material_spec_business_id` field broke every existing test
  that called the create-draft endpoint directly (`tests/test_material_specification.py`'s entire file, plus
  3 call sites in `tests/test_recipe_master.py`) — `CommandEnvelope`'s `extra="forbid"` turns a now-unknown
  field into a 422 on every one of them. All fixed (9 existing + 3 cross-file + 7 new = 19 passing); a direct
  grep sweep confirmed no other API caller (only direct-ORM test fixtures elsewhere, which are unaffected)
  still sends the removed field.
- **Verified live:** created a real material + spec draft with no business_id/version_no supplied (correctly
  auto-derived/auto-incremented), added two criteria rows, confirmed them in the detail response, released
  with an independent QA Releaser (criteria visible in the signed snapshot), then confirmed further
  criterion mutation is correctly blocked post-release (`INVALID_TRANSITION`).

**Part B — AI-advisory document-based spec auto-extraction — HELD 2026-10-05 (user decision).** Investigated
the real shape of the work: `app/modules/ai_governance/` already has a complete Document 105 governance
pipeline (register use case → risk-assess → approve model deployment [signed, QA Releaser, policy already
exists] → register prompt → `execute_ai_advisory()`, which takes a pluggable `model_client` callable — the
audit/fail-closed/logging wrapper is already built). Zero AI use cases are registered anywhere in this live
system, though, so this would be the first real one through that pipeline. The real work isn't new
governance code — it's (1) an actual LLM call (Anthropic via `httpx`, already a dependency, no Document 104
needed) sending uploaded spec PDFs to an external provider at real per-call cost, and (2) the one-time
bootstrap data (use case/risk/deployment/prompt). **User held this**, correctly treating the
external-cost/data-privacy decision as needing more thought rather than being rushed past it. Resume by
re-reading this note — the governance-pipeline research above doesn't need redoing.

- **Client requirements covered:** 2.5 (Part A fully; Part B — document-based auto-extraction — still open).
- **Dependencies:** Phase 4 (fulfillment-path selection here feeds directly into how Phase 6's receipt testing behaves).
- **Open questions:** Material "Type" field and "Active/Inactive" meaning were both explicitly deferred by the client — do not bundle into this phase without a follow-up confirmation. Part B's parsing/extraction mechanism is a new open question (see above).

### Phase 6 — Material Receipt / Examine Merge + Service Provider + Testing-Pathway Integration — IMPLEMENTED 2026-10-05
- **Objective:** Merge Receipt+Examine into one screen, apply the field renames/restructuring (Identity→Matched-with-PO, split Damage checks, drop Contamination, Seal Intact, "Examination Notes"→"Shipment Examination Notes", "(Optional)" labeling + "Not Applicable" toggle on Lot Number fields — see 2.9), extend Supplier with a Service Provider concept, and wire the three testing pathways (In-House/External/COA) into the Phase 4 Global QC module.
- **Client requirements covered:** 2.6 in full (except the explicitly deferred container/barcode and PO-module items).

**The architectural fork, resolved with the user before any code:** Phase 5 built `MaterialSpecificationCriterion` as a simple declarative "spec sheet" with a `fulfillment_path` column that nothing downstream read. Investigation found the real lot-release gate (`material.commands._missing_required_tests`) is driven entirely by a separate, pre-existing `qc.QcTestSpecification`/`QcTestDefinition` pipeline, authored independently via the QC Specifications screen — meaning a QA person would otherwise author the same test twice with no link between the two. User chose **auto-sync criteria → QcTestDefinition** over the two alternatives (leave them disconnected; or bypass QcTestDefinition entirely from the receipt UI, which would have left the real release gate blind to the new criteria).

**What was built:**
1. **Receipt+Examine merge (frontend only):** `CreateReceiptModal` now captures the created receipt's `MutationReceipt` directly (bypassing the generic `useCommand` wrapper, which discards the response) and immediately opens `ExamineReceiptModal` with a minimal stub record, instead of returning the user to the list to find the row and click "Examine" separately. The two backend commands (`CreateMaterialReceipt`/`ExamineReceipt`) stay distinct — only the UI became continuous.
2. **Field relabel/restructure:** "Identity Confirmed" → "Material matched with PO/Material number" (label only). "Damage Observed" split into `shipping_damage_observed`/`container_damage_observed` (migration 0136, two new nullable columns on `material_receipts`); the legacy `damage_observed` column stays and is now derived server-side as their OR (MIG-FR-004 — no drop this release). "Contamination Observed" removed from the command/UI entirely (column stays, unwritten going forward — `CommandEnvelope`'s `extra="forbid"` now rejects the old field with 422 rather than silently ignoring it). "Seal Broken" → "Seal intact?" Yes/No, with a required free-text note when the answer is "No" (folded into `examination_notes` at submit time — no new backend field). "Examination Notes" relabeled "Shipment examination notes". Supplier's/Manufacturer's Lot Number fields gained a "Not applicable" checkbox (pure UI affordance — both states already stored `null`, no backend change).
3. **Service Provider:** `Supplier.role_type` gained `"service_provider"` as a fourth allowed value (app-level validation only — no DB CHECK constraint existed to migrate).
4. **Equipment Calibration provider picker:** `EquipmentCalibration.provider_supplier_id` (new nullable FK, migration 0136) lets an external calibration reference a known Supplier (`role_type` `service_provider`/`both`) via a dropdown; free-text `provider_name` stays as a fallback for a not-yet-onboarded provider and is auto-derived from the Supplier's `legal_name` when a supplier is picked without one.
5. **QC external-lab provenance:** `QcTestOrder.external_provider_id` + `external_report_hash` (new nullable columns, migration 0136) record which Supplier performed a test sent to an external lab, and a hash of the report relied upon. Reuses the entire existing QC pipeline (`create_sample`→`create_test_order`→`record_result`→`review_test_order`) unchanged — the only difference from an in-house test is these two extra fields.
6. **The bridge:** `release_material_spec_version()` now calls `qc_commands.create_test_specification_draft()` in the same transaction after collecting the released criteria: every criterion with `fulfillment_path` in `("in_house", "external_lab")` becomes a `required=True, release_blocking=True` `QcTestDefinition` (one test definition per criterion, `result_data_type="qualitative"` — the spec rows are free-text acceptance descriptions, not structured numeric rules, so there's no automated accept/reject rule to bind) under a new `QcTestSpecification` scoped to that exact `MaterialSpecificationVersion` (`spec_code = f"{business_id}-V{version_no}-QC"`, one spec per released version so lineage never collides across versions). It is drafted, **not auto-released** — a human QA signature via the existing QC Specifications screen is still required (AG-07/SIG-FR-006, no shortcut around Part 11). A `supplier_coa` criterion (or one with no `fulfillment_path` set) is deliberately skipped: that case is already covered by the existing lot-level `coa_reliance` override (migration 0126, Client_Decisions_Neededanswers Topic 1/2) — there is no in-house/external test to schedule for it, and inventing a second mechanism would duplicate an already-approved one. A version released with only `supplier_coa`/unset criteria creates no QC spec at all (verified by test — no empty, pointless draft).

- **Migration:** `e3a5c7f9b1d6` (0136) — additive only, no backfill, forward+rollback verified on both the live and test databases.
- **Files changed:** `app/modules/material/{models,commands,router}.py`, `app/modules/equipment/{models,commands}.py`, `app/modules/qc/{models,commands,router}.py`, `app/modules/material_specification/commands.py`, `app/modules/supplier_quality/{models,commands}.py`; frontend `app/material-receipts/page.tsx`, `app/equipment/[id]/page.tsx`, `app/qc/samples/[id]/page.tsx`, `app/suppliers/page.tsx`.
- **Tests:** 11 new tests added (`test_material_specification.py` ×2 — auto-sync populates/skips correctly; `test_supplier_quality.py` ×2 — `service_provider` accepted, unknown role_type rejected; `test_equipment_flow.py` ×2 — provider picker derives name, wrong-role-type rejected; `test_qc.py` ×1 — external provider persists/validates; `test_material_receipt_flow.py` ×3 — container-damage-alone still holds, legacy `damage_observed` OR-derived, removed `contamination_observed` field now rejected; plus fixed call sites in 5 existing test files whose raw examine payloads used the old field names). Full run across all 9 touched test files: **119 passed, 0 failed** (two batched runs: 97 passed covering receipt/dispensing/inventory/storage/qc-sample fixups, then 119 passed covering specification/supplier/equipment/qc/receipt including the new Phase 6 tests — some files run twice as edits landed, final state of each file is green).
- **Not forced into `traceability/TRACEABILITY_MASTER.csv` or `status/build-status.json`:** same reasoning applied to every phase in this gap-analysis track — those files are keyed to the formal Document 01-115 requirement-ID baseline with pre-written test-case IDs; this is client-driven work outside that baseline, and fabricating conformance rows would violate the "no fabricated evidence" rule.
- **Dependencies:** Phase 4 (testing engine) and Phase 5 (structured spec rows with fulfillment-path) — both already landed.
- **Open questions / deliberately not done:** Purchase Order module (to back real Ordered Quantity / PO matching) stays out of scope — flagged, not silently half-built. The QC Specifications screen was not changed — an auto-drafted spec surfaces there automatically through its existing generic listing, with no new UI needed to find/release it.

### Phase 7 — Equipment Enhancements — IMPLEMENTED 2026-10-05
- **Objective:** Bulk equipment import, computer-system-operated flag, New/Old equipment path, QC-sign-off gate on equipment eligibility, calibration field resequencing + Service-Provider dropdown, "Standard Reference"→"Standard/Traceable Reference" relabel, Pass capitalization consistency, "Not Applicable" toggle for Firmware Version, maintenance activity checklist, breakdown→recalibration gating.
- **Client requirements covered:** 2.7 (except explicitly deferred CSV questionnaire detail, New/Old equipment detailed rules, maintenance-specification design, and detailed breakdown critical/non-critical rules — see below).

**Re-verified against current code before building (same discipline as every phase):** the QC-sign-off gate row in this doc's own §2.7 table already said "Done" — Phase 4's `CALIBRATION_APPROVAL_PENDING` reason *is* that gate, confirmed still true; no new work there. The calibration provider FK was already done in Phase 6. That left: `is_computer_operated`, breakdown→recalibration gating, the maintenance activity checklist, bulk import, and the small relabel/resequence/capitalization items.

**The one real architectural question, resolved with the user before any code:** the equipment module's own docstring declares exactly 4 authoritative entities ("no 5th table is added" — Document 38 §5), and this freeze was already taken seriously once before: `EquipmentClass` (needed for a different feature, 2026-09-16) was deliberately routed to `recipe_master` instead of added here, specifically to avoid breaking it. The maintenance activity checklist (repeatable Activity/Result rows) wanted the same child-table shape Phase 5 used for Material Specification criteria — but that module never declared a hard freeze. Presented both options; **user chose a JSONB array column** (`MaintenanceWorkOrder.activities`, same precedent as the existing `parts_used` column) over a new table, respecting the freeze.

**What was built:**
1. **`is_computer_operated`** (`EquipmentAsset`, migration `f5c7e9b1d3a8`/0137) — mandatory-at-creation question (required field, no default, same treatment Phase 6 gave the Material Receipt examine booleans). The Computer System Validation questionnaire it would branch into stays explicitly deferred.
2. **Breakdown → recalibration gate:** `EquipmentAsset.recalibration_required` + `MaintenanceWorkOrder.non_critical` (migration 0137). A breakdown work order not flagged non-critical sets the asset's flag; a new `RECALIBRATION_REQUIRED` reason joins `_ineligibility_reasons()` (same shared predicate `return_to_service`/`get_eligibility` both already use, so the existing generic "Not eligible for use" banner on the equipment detail page surfaced it automatically, no new frontend wiring needed for that part). Cleared only when a *new* calibration is recorded **and approved** — the same two-step bar `CALIBRATION_APPROVAL_PENDING` already applies to a plain passing result; a verified maintenance work order alone is not enough. Detailed critical/non-critical rules stay deferred — this ships the binary flag only, with the client's own example (a mere power-supply failure) as the frontend's hint text.
3. **Maintenance activity checklist:** `MaintenanceWorkOrder.activities` (JSONB array of `{activity, result}`), recorded at the **completion** step (`CompleteMaintenanceModal`), not creation — matches when the actual work and its outcomes are actually known. Shown only for `type="planned"` work orders.
4. **Bulk equipment import:** new `bulk_import_equipment`/`validate_bulk_import_equipment_rows` commands and `POST /equipment/v1/assets/bulk-import/{preview,commit}` — a new capability beyond Document 38 §6's declared 9 operations, same "own considered contract, not a guessed one" precedent as Phase 1's `bulk_import_users` and the Warehouse Location/Aseptic Profile `create` additions before it. Exact same preview/all-or-nothing-commit shape as Phase 1, reusing `create_equipment_asset` per row rather than bypassing its validation. `equipment_class_code` (not a raw id) is the one thing a spreadsheet realistically carries by hand, mirroring Phase 1's `role_name`/`site_code` choice.
5. **Calibration form resequencing + relabels:** field order now follows the client's requested sequence (Performed date → Internal/External → Standard/Traceable Reference *or* Provider+Certificate → Result → Next due date). "Standard Reference" relabeled "Standard/Traceable Reference". "Approved/Not-Approved" deliberately stayed a separate second-step call (the existing approval ceremony) rather than folded into this form — that's a different actor/time, not just a field position, and moving it would have been a guessed workflow change, not a label change.
6. **"Pass" capitalization:** display-only (`Pass`/`Fail`/`OOT (out of tolerance)` in the result dropdown and history table); the stored value stays lowercase (`pass`/`fail`/`oot`) — no data/contract change. Same convention noted but **not yet applied to Material/QC's own result displays** — out of this phase's module boundary, flagged as a known remaining item.
7. **"Not Applicable" toggle (Firmware Version)** and **"(Optional)" labeling** on the equipment creation form — pure UI affordances, same pattern as Phase 6's Lot Number fields.

- **Migration:** `f5c7e9b1d3a8` (0137) — additive only (2 new boolean columns defaulted on `equipment_assets`, 1 boolean + 1 JSONB on `maintenance_work_orders`), no backfill, forward+rollback verified on both live and test databases before any model/command code was written.
- **Files changed:** `app/modules/equipment/{models,commands,router}.py`, `app/mutation/errors.py`; frontend `app/equipment/page.tsx`, `app/equipment/[id]/page.tsx`; `lib/api.ts`.
- **Tests:** 6 new tests in `test_equipment_flow.py` (recalibration gate blocks then clears only after a new approved calibration; non-critical breakdown skips the gate; `is_computer_operated` required/persists; activity checklist round-trips; bulk-import preview/all-or-nothing-commit including an unknown `equipment_class_code` rejection). Required-field fixups applied across the 5 existing test files that create equipment assets (`test_cleaning_flow.py`, `test_aseptic_flow.py`, `test_em_flow.py`, `test_sterilization_flow.py`, `test_equipment_flow.py` itself) — same "the whole tree, not just the owning module's test file" discipline the Phase 5/6 field-rename work established. Full run across all 5 touched files: **113 passed**; `test_equipment_flow.py` alone re-run after the new tests: **48 passed, 0 failed**.
- **Not forced into `traceability/TRACEABILITY_MASTER.csv` or `status/build-status.json`:** same reasoning as every phase in this track.
- **Dependencies:** Phase 1 (import framework, reused), Phase 4 (QC gate, already done), Phase 6 (Service Provider, already done).
- **Deliberately not done:** New/Old equipment toggle and its detailed skip-IQ/OQ/PQ rules (client explicitly deferred — building just the flag with no real effect would have been a half-finished feature, not a smaller version of the real one); the Computer System Validation (21 CFR Part 11) questionnaire sub-workflow; Maintenance Specification + acceptance criteria (client asked to hold this entirely, pending their own design doc); detailed breakdown critical/non-critical rules (binary flag only shipped); "Pass" capitalization in Material/QC displays (flagged, not this phase's module).

### Phase 8 — Product Master Cleanup (lower priority, partially specified) — IMPLEMENTED 2026-10-06
- **Objective:** Apply the same Business-ID-removal and name-field-merge pattern as Material/Supplier; reorder fields (Product Family → Code → Name → Strength, per 2.9); hide (not delete) Manufacturing Profile from client-facing views; add bulk Excel import (reusing Phase 1's framework, per 2.8); investigate category-specific field branching.
- **Client requirements covered:** 2.8 (partial — meeting was cut short before this was fully discussed).

**Re-investigated every item against current code before touching anything**, since this phase's own open-questions note said "essentially everything here needs re-confirmation" and several table rows were explicitly marked "not independently verified this pass." Findings genuinely changed the scope:
- **Duplicate name fields — doesn't exist.** No `brand_name` anywhere in the codebase; `ProductVersion` has exactly one `name` column, and the create/edit forms each render exactly one Name field. Dropped from scope — nothing to merge.
- **Category-specific fields — confirmed nothing exists** (only two loosely-related, independently-evolved fields — `manufacturing_profile_code` and the already-flagged-provisional `combination_product_type` — neither a governed category taxonomy). Stays client-deferred as planned; nothing built.
- **"Business ID" removal and "Manufacturing Profile" hide both turned out more load-bearing than the doc assumed** — presented both as real forks to the user before writing any code, rather than blindly copy-pasting the Material/Supplier precedent:
  - *Business ID*: unlike Material (which derives its business id from an existing parent `material.code`), Product Master has no parent entity — `product_business_id` is itself the stable version-chaining identity key (unique with `version_no`), separate from `product_code` (also stable once generated). **User's decision: remove it from the frontend form entirely; auto-generate on submit.** Implemented as a true backend change (not just hiding a field): `CreateProductDraftCommand.product_business_id` is now optional, auto-generated via `codegen_service.next_code(entity_type="PRODUCT_BUSINESS_ID", prefix="PRDB")` for a brand-new product (`version_no == 1`) — same shape `product_code` already used. **Real gap this surfaced and closed without being asked:** a further version of an *existing* product still needs to say which product it belongs to (no "prior version" fallback is possible for an identity key), and the single "New product draft" modal was previously the only way to create v2+ (by hand-retyping the same business id). Added a dedicated "New version" action on the product's Versions history card that pre-fills the existing `product_business_id` (read, never retyped) and the next version number, so that capability isn't silently lost.
  - *Manufacturing Profile*: confirmed non-cosmetic — it's a required (`nullable=False`) field read by two real backend gates (product release-readiness/sterile-profile matching in `service.py::validate_completeness`, and DDCP profile-family authoring in `ddcp/commands.py::_assert_product_version_for_profile`, which blocks authoring an Injectable or Inhalation DDCP profile unless this value matches). **User's decision: keep it visible, move it to an Advanced section.** Implemented as a `<details>`/`<summary>` collapsible (same pattern already used on `/rules`) wrapping the still-required dropdown — addresses the "don't clutter the main form" complaint without breaking either gate.
- **Field reorder** (§2.9: Product Family → Code → Name → Strength) — done as asked; Strength value/UOM pulled out of the "Combination product" grouping it was previously nested in, since the client's requested order treats it as a top-level field.
- **Bulk import** — confirmed zero existing capability (not even partial). Built `bulk_import_products`/`validate_bulk_import_product_rows` and `POST /products/v1/drafts/bulk-import/{preview,commit}`, same preview/all-or-nothing-commit shape as Phase 1 (users) and Phase 7 (equipment), reusing `create_draft()` per row. Always creates version 1 of a brand-new product (first-time bulk onboarding, not a bulk version-adder, matching its two precedents exactly) — `product_business_id` is never part of a bulk row, always auto-generated. The nested `constituents` list on the single-row command has no flat-CSV equivalent, so bulk-imported drafts start with none (edited afterward via the normal single-record UI), same "not every optional field needs a CSV column" precedent Equipment's own bulk row already set (`product_family_code` resolved the same "business code, not a UUID" way `equipment_class_code` was).

- **Migration:** none needed — `product_business_id` was already a column; making it optional on the command and auto-generating it reuses the existing `codegen` sequence-counter table with a new `entity_type`/`prefix` pair (no schema change).
- **Files changed:** `app/modules/product_master/{commands,router}.py`; frontend `app/product-master/page.tsx`; `lib/api.ts`.
- **Tests:** 4 new tests in `test_product_master.py` (auto-generation at v1; v2-without-business-id correctly rejected since there's no fallback; bulk-import preview/all-or-nothing-commit including an unknown `manufacturing_profile_code` rejection). **Also found and fixed 2 pre-existing, unrelated bugs while verifying the 10 other test files that call `POST /products/v1/drafts`** (neither caused by this phase — confirmed via `git diff` showing zero prior modification to the files involved): (1) `test_workflow_notifications.py` imported `test_material_specification.py`'s `_draft_body` helper and called it with a 3rd positional arg (`material_spec_business_id`) that Phase 5's business-id removal had already dropped from that helper's signature weeks of session-time earlier — a cross-file caller the Phase 5 sweep missed; fixed the call site and the entity-label assertion it fed. (2) `test_rebuild_covers_every_registered_aggregate_type` hardcoded `len(...) == 18` against a notifications registry that already had 19 real entries (pre-existing drift, unrelated to any module this session touched) — fixed to assert against `len(WORKFLOW_SPECS)` itself so it can't silently go stale again. Full run across all 12 affected test files: **all passing** (44 in the `test_workflow_notifications.py`+`test_product_master.py` pair alone, including both fixed tests and all 4 new ones; 192+ passed with zero unrelated failures across the other 10).
- **Not forced into `traceability/TRACEABILITY_MASTER.csv` or `status/build-status.json`:** same reasoning as every phase in this track.
- **Dependencies:** Phase 1 (bulk-import framework, reused).
- **Deliberately not done:** category-specific field branching (confirmed nothing exists, stays client-deferred); "Manufacturing Profile" was kept, not hidden, per the user's explicit choice once its real backend load became clear; no Excel (.xlsx) parsing — CSV only, same choice Phase 1 made for the same reason (no new parsing dependency).
- **Open questions:** Recipe/Batch/SOP, which the client named as "next," remain untouched — not covered by any transcript reviewed in this gap analysis and would need a dedicated follow-up session.

---

## Open Questions Requiring Client Decision (consolidated)

1. ~~**(Blocking, Phase 0)** Tenancy model~~ — **RESOLVED 2026-10-05: one deployment per client company.**
2. Exact first-time-onboarding spreadsheet template (users) — **Phase 1 shipped with
   `full_name,email,role_name,site_code` as a working default; confirm with the client before relying on
   it for a real onboarding, since it wasn't separately re-confirmed with them.**
3. "Minimum certification by risk class" supplier gating rule — confirm in/out of scope.
4. Material "Type" classification and the meaning of Material "Active/Inactive" — client deferred both to himself.
5. Is the separately-in-development "newer QC Testing module" the client referenced actually `app/modules/qc/` (built 2026-09-21)? If confirmed, the client's assumed "complex calculation, 5 years away" scope is largely already addressed by the existing rule engine — worth telling them directly, since it changes their own mental model of what's left to build.
6. Purchase Order module — is this wanted now (to back real Ordered Quantity / PO matching in Material Receipt), or deliberately out of scope?
7. Computer System Validation (CSV) questionnaire detail — client said he'd send a design separately.
8. Old-equipment onboarding rules (what exactly gets skipped/backfilled) — client said he'd consult peers and get back to us.
9. Maintenance Specification + Acceptance Criteria design — client explicitly deferred, said he'd send a proper design later.
10. Breakdown-maintenance critical/non-critical distinction rules — client explicitly deferred.
11. ~~Equipment document upload~~ — resolved during this analysis, no client decision needed (already built via the generic `evidence` module).
12. Product Master — essentially the whole domain needs a follow-up session; the transcript cuts off mid-discussion.
13. Sampling Quantity rules (per-test, at spec-definition time) — client explicitly deferred.
14. Sampling Plan / Quality Plan document-tab integration design — client explicitly deferred, called it a stopgap.
15. Retest workflow — client explicitly deferred as "a whole new subject"; worth noting the `qc` module already has schema groundwork for it (`OosRetestPlan`/`OosResamplePlan`/`max_retests`), same pattern as item 5 above.

---

## Traceability Note

None of the items above have assigned requirement IDs yet, since they originate from a client meeting rather
than the controlled spec documents (01–115). Per CLAUDE.md §4, any item that changes regulated behavior,
record authority, signature requirements, or validation acceptance will get a `docs/generated/18_SPEC_GAPS.md`
entry (not just a line in this planning doc) once a phase is approved and scoped for real implementation. Items
that are pure UX/wording/field-removal and don't touch regulated semantics will be tracked through normal
`traceability/TRACEABILITY_MASTER.csv` rows at implementation time, same as any other work package task.

---

## Next Step

Per your workflow: **I'm stopping here.** Nothing above has been implemented. Let's go through Phase 0 first
(it gates everything else), then walk Phases 1–8 one at a time — for each, I'll explain what changes, why,
what existing functionality it touches, and where I need your (or the client's) decision before proceeding.
