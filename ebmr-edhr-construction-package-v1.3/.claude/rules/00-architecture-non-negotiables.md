# Architecture non-negotiables

**Purpose:** Architecture non-negotiables for the eBMR/eDHR platform.
**Applicable paths/modules:** see `docs/generated/17_REPOSITORY_STRUCTURE.md`; this rule applies to every
service, the Frappe app, edge and integration code unless a narrower scope is stated below.
**Source documents:** Document 01 (DOC-001), Document 02 (DOC-002), Document 98 (SPEC-ENG-002), Document 69 (SPEC-DATA-001), Document 71 (SPEC-DATA-003)
**Source requirement IDs:** C-001..069 (69); MAT-001..022 (22); ST-001..020 (20); QMS-001..018 (18); CP-001..020 (20); PM-001..010 (10); MD-001..025 (25); PH-001..030 (30); SPEC-SEC-001..001 (1); ARC-001..018 (18); MUT-001..015 (15); SIG-001..016 (16); AGT-FR-001..036 (36); DATA-FR-001..030 (30); MDB-FR-001..028 (28)

---

## Mandatory rules

**AG-01** — Frappe Framework is the UI/application/configuration framework. ERPNext is NOT a base layer — it is an optional external ERP integration target only (Doc 48/49).

- Forbidden: Fork or edit of Frappe core; patching core files; monkey-patching core methods; installing ERPNext into the platform runtime; importing ERPNext models/SDK types into GxP packages.
- Required: Custom Frappe app in `apps/ebmr_frappe` only; Frappe as a pinned external dependency, never vendored; all core interaction through public APIs/hooks; ERPNext reached only through the Doc 49 adapter over public APIs.

**AG-02** — Proprietary GxP Core is independent product IP.

- Forbidden: Embedding regulated domain logic inside Frappe DocType controllers.
- Required: Regulated logic lives in `services/*`; Frappe calls it over the GxP API.

**AG-03** — PostgreSQL is authoritative for proprietary regulated GxP state.

- Forbidden: Authoritative regulated writes to MariaDB; regulated read used for a decision from a projection.
- Required: Authoritative read/write against PostgreSQL through the owning service.

**AG-04** — Frappe/MariaDB holds framework/UI/configuration and controlled non-authoritative projections.

- Forbidden: Projection DocType without authoritative_source_id/version/projected_at; user-editable projected GxP field.
- Required: Read-only projected fields with source id/version/timestamp per Doc 71 MDB-FR-003.

**AG-05** — One authoritative owner/store per regulated entity.

- Forbidden: Second writable copy of a regulated entity in another service or database.
- Required: Ownership recorded in `docs/generated/05_DATABASE_OWNERSHIP_MATRIX.md`; others read by contract.

**AG-06** — Regulated mutations go through the Mutation Gateway / owning domain command.

- Forbidden: `frappe.db.set_value()` on regulated data, raw SQL UPDATE from a non-owning service, generic PATCH endpoint.
- Required: `POST /gxp/v1/commands/{commandType}` with expected_version and idempotency key.

**AG-07** — Login/MFA is not an electronic signature.

- Forbidden: Treating an authenticated session as signature evidence; client-asserted signature flags.
- Required: Fresh step-up signature ceremony bound to record/version/hash/meaning (Doc 04).

**AG-08** — Audit / Vault / evidence history is immutable and superseding.

- Forbidden: UPDATE or DELETE on audit or released record versions; editing a failed test or OOS result.
- Required: Append-only supersede with reason, actor, UTC time and prior-version retention.

**AG-09** — PostgreSQL transactional outbox is the authoritative event source; NATS is transport.

- Forbidden: Publishing to NATS from application code before/without the committed outbox row.
- Required: Domain state + version + audit + outbox in one transaction; publisher reads outbox after commit.

**AG-10** — Temporal orchestrates workflows but is never regulatory truth.

- Forbidden: Storing regulated state only in workflow variables; deriving release decisions from workflow history.
- Required: Workflow calls domain commands; authoritative state re-read from the owning service.

**AG-11** — Cache/search/read models are rebuildable and non-authoritative.

- Forbidden: Signing, releasing or dispositioning from a Redis/search/report value.
- Required: Authoritative re-read before any regulated decision or signature.

**AG-12** — Object evidence is hash-controlled and immutable/WORM-capable.

- Forbidden: Overwriting an evidence object in place; storing evidence without digest/manifest.
- Required: Content-addressed write + manifest + retention/legal-hold policy (Doc 72).

**AG-13** — ERP/LIMS/Edge integrate through controlled APIs/events with reconciliation.

- Forbidden: Adapter writing directly into GxP tables; ERP status mapped automatically to QA release.
- Required: Adapter → integration command → Mutation Gateway; reconciliation ledger and replay control.

**AG-14** — AI is advisory only.

- Forbidden: AI tool with authority to sign, release, disposition, approve, alter audit or submit a report.
- Required: AI proposes; a qualified human executes through the normal authorization/signature/mutation path.

**AG-15** — No regulated behavior is guessed.

- Forbidden: Silent reconciliation of conflicting specifications; inventing a signature/retention/precision rule.
- Required: Create a SPEC_GAP entry in `docs/generated/18_SPEC_GAPS.md` and stop on the affected scope.

## Required implementation pattern

Logical service boundaries from Document 02 §11 are mandatory even when deployment units are consolidated
into `services/gxp-api`. A module never imports another module's repository or reaches into its tables;
it calls the owning module's command or query interface.

## Completion checks

- `tooling/guardrails` checks pass.
- No new path outside `docs/generated/17_REPOSITORY_STRUCTURE.md`.
- Any deviation recorded as an ADR in `docs/adr/`.

## SPEC_GAP triggers

Any requirement that appears to demand a second authoritative store, a bypass of the Mutation Gateway,
an editable audit record, or AI authority over a regulated decision.


## Source requirements (extract)

| ID | Requirement | Required behaviour |
|---|---|---|
| C-001 | Organization & Legal Entity | Represents the regulated manufacturer, business entity and operating organization responsible for records. It separates corporate ownership from manufacturing sites and forms the root of authorization |
| C-002 | Manufacturing Site | Represents each FDA-regulated manufacturing facility. All batches, equipment, personnel, warehouses and quality events must belong to a defined site. |
| C-003 | Building / Area / Room / Line | Creates the physical manufacturing hierarchy required to determine where each regulated operation took place. Supports contamination controls, equipment location and authorized-area rules. |
| C-004 | Department / Function | Defines Production, QA, QC, Warehouse, Engineering and other organizational functions. Required for responsibilities and segregation of duties. |
| C-005 | Shift Management | Records production shifts and associates operators and activities with the active shift. Useful for investigations, operational reviews and traceability. |
| C-006 | Unique User Identity | Every human must use a unique identity. Shared Production, QA or Admin accounts must not be permitted for regulated actions. |
| C-007 | Role Based Access | Determines what operators, supervisors, QA, QC, engineering and administrators may see and perform. |
| C-008 | Segregation of Duties | Prevents conflicting activities, for example an operator independently approving their own exception or QA release where independent review is required. |
| C-009 | Employee Qualification | Associates users with qualifications such as dispensing operator, sterile-area operator, QA reviewer or specific equipment authorization. |
| C-010 | Training Status | Links SOP/training requirements to users and their effectiveness or completion status. Expired/missing training can automatically block applicable activities. |
| C-011 | Temporary Authorization | Supports documented temporary qualification or emergency access with start/end date, justification and approval. |
| C-012 | Product Master | Defines product identity, code, dosage/device configuration, manufacturing type, lifecycle status and associated regulatory configuration. |
| C-013 | Raw Material Master | Defines APIs, excipients, components, packaging materials and device components used during manufacturing. |
| C-014 | Specification Master | Stores approved specifications including acceptable ranges, units, methods and effective periods. |
| C-015 | Unit of Measure | Defines controlled units and conversion rules. Prevents uncontrolled textual units and calculation ambiguity. |
| C-016 | Supplier / Manufacturer | Identifies manufacturer/supplier sources for received materials and components. |
| C-017 | Material Quality Status | Supports quarantine, sampled, under-test, approved, rejected, expired and other controlled states. |
| C-018 | Expiry / Retest | Tracks expiry/retest dates and automatically prevents use when material validity has elapsed. |
| MAT-001 | Supplier Master | supplier identity; manufacturer identity; addresses; status; approved materials; qualification links; regulatory certificates; effective status |
| MAT-002 | Supplier Qualification | qualification request; questionnaire; audit; risk classification; approval; expiry/requalification; suspension; disqualification |
| MAT-003 | Approved Supplier List | material-to-approved-supplier relationship; site applicability; effective dates; exceptions; change history |
| MAT-004 | Purchase Requisition | requester; material/specification version; required quantity/date; site; approval; ERP synchronization |
| MAT-005 | RFQ / Supplier Quote | RFQ issue; quote receipt; commercial comparison; supplier selection; attachment retention |
| MAT-006 | Purchase Order | material/spec version; supplier/manufacturer; quantity; delivery terms; approval; ERP synchronization |
| MAT-007 | Material Receipt / GRN | PO match; received quantity; manufacturer lot; supplier lot; internal lot; container IDs; receipt date; damage inspection |
| MAT-008 | COA Management | COA attachment; supplier test values; document authenticity metadata; version; review; discrepancy handling |
| MAT-009 | Quarantine | automatic quarantine at receipt; location restriction; status labels; access control |
| MAT-010 | Sampling | sampling plan; sample quantity; sampler; sample IDs; container selection; chain of custody; LIMS transfer |
| MAT-011 | QC Disposition | pending; released; rejected; conditional/use-under-deviation if allowed; retest; expiry/retest |
| MAT-012 | Warehouse/Location | warehouse; zone; bin; environmental requirement; restricted area; status segregation |
| MAT-013 | FEFO / Eligibility | expiry/retest; released status; site; product applicability; reservation; blocked lot; deviation override |
| MAT-014 | Material Reservation | batch reservation; quantity; expiry; release; conflict handling |
| MAT-015 | Material Issue | issue to batch/area; scan verification; lot/container; quantity; operator |
| MAT-016 | Material Dispensing | target; tolerance; balance; actual quantity; verifier; potency adjustment; labels |
| MAT-017 | Material Return | unused quantity; container state; return location; status reevaluation |
| MAT-018 | Inventory Adjustment | controlled adjustment; reason; independent approval where required; audit |
| MAT-019 | Destruction | destruction request; authorization; quantity; witness; method; evidence |
| MAT-020 | Reconciliation | received/issued/dispensed/consumed/returned/destroyed variance; tolerance; exception |
| MAT-021 | Material Genealogy | supplier/manufacturer lot → internal lot → container → batch → finished product |
| MAT-022 | ERP Synchronization | master sync; PO sync; inventory quantity/value sync; consumption posting; retry/reconciliation |

## SPEC_GAP triggers

Raise a SPEC_GAP rather than deciding, if you encounter: a missing signature/authorization/retention/
precision value, a conflict between two source documents, an entity without an owner, an event without a
producer, or any requirement that would need a regulated behaviour you cannot trace to
Document 01, Document 02, Document 98, Document 69, Document 71 or Documents 106–115.
