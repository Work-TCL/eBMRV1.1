# WP-04 — Scope & Requirements

**In scope:** Documents 18, 19, 20, 21, 22, 23, 24, 25

## Document 18 — Procurement & Supplier Quality Specification (SPEC-MAT-001)

- Code location: `services/gxp-api/src/modules/materials`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: SUP-FR-001..032 (32)

## Document 19 — Material Receipt, Quarantine & Quality Status Specification (SPEC-MAT-002A)

- Code location: `services/gxp-api/src/modules/materials`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: RCV-FR-001..032 (32)

## Document 20 — Inventory, Lot/Container & Warehouse Specification (SPEC-MAT-002B)

- Code location: `services/gxp-api/src/modules/materials`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: INV-FR-001..032 (32)

## Document 21 — Material Dispensing & Weighing Specification (SPEC-MAT-002C)

- Code location: `services/gxp-api/src/modules/materials`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: DSP-FR-001..032 (32)

## Document 22 — Material Consumption, Return, Adjustment, Destruction & Reconciliation Specification (SPEC-MAT-002D)

- Code location: `services/gxp-api/src/modules/materials`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: CON-FR-001..032 (32)

## Document 23 — Native Basic QC & Sampling Specification (SPEC-QC-001)

- Code location: `services/gxp-api/src/modules/qc`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: QC-FR-001..038 (38)

## Document 24 — LIMS Integration Architecture & Generic Adapter Contract (SPEC-QC-002)

- Code location: `services/gxp-api/src/modules/qc`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: LIMS-FR-001..034 (34)

## Document 25 — OOS / OOT Management Specification (SPEC-QC-003)

- Code location: `services/gxp-api/src/modules/qc`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: OOS-FR-001..030 (30); OOT-FR-001..010 (10)

## All requirements

| ID | Doc | Requirement | Behaviour | Acceptance |
|---|---|---|---|---|
| SUP-FR-001 | 18 | Supplier master | Maintain supplier legal identity, business name, addresses, sites, contacts, manufacturer-vs-distributor role, external IDs and lifecycle status. | One controlled supplier identity. |
| SUP-FR-002 | 18 | Manufacturer master | Separate actual manufacturer identity from commercial supplier/distributor where different. | Manufacturer genealogy exact. |
| SUP-FR-003 | 18 | Supplier qualification request | Initiate qualification for supplier/site/material category with scope, risk, requested evidence and owner. | Qualification controlled. |
| SUP-FR-004 | 18 | Supplier risk classification | Classify supplier/material criticality using released risk methodology and product/profile applicability. | Controls proportional. |
| SUP-FR-005 | 18 | Qualification evidence | Store questionnaire, certifications, licenses, audits, capability evidence, quality agreements, test history and attachments as versioned evidence. | Review basis retained. |
| SUP-FR-006 | 18 | Supplier audit | Plan/record audit scope, date, auditors, findings, response, CAPA/SCAR links and approval. | Supplier audit inspectable. |
| SUP-FR-007 | 18 | Supplier approval | Approve supplier for specific manufacturer site/material/specification/category/site/customer scope, not blanket global approval by default. | ASL granular. |
| SUP-FR-008 | 18 | Approved Supplier List | Maintain effective-dated supplier-material/site approval matrix with status Approved, Conditional, Suspended, Disqualified, Expired. | Procurement eligibility deterministic. |
| SUP-FR-009 | 18 | Requalification | Define expiry/review frequency/risk trigger; generate due alerts and block new procurement if policy requires. | Approval current. |
| SUP-FR-010 | 18 | Suspension | Quality can suspend supplier/material relationship with reason/signature; open PO/receipt impact assessed separately. | No silent continued use. |
| SUP-FR-011 | 18 | Disqualification | Permanent/controlled disqualification retains history and affected material/product impact. | Historical evidence preserved. |
| SUP-FR-012 | 18 | Conditional approval | Support temporary/conditional supplier use under defined scope, expiry, justification, enhanced inspection/testing and approval. | Exception bounded. |
| SUP-FR-013 | 18 | Quality agreement | Reference controlled quality agreement version, effective dates and obligations; renewal/expiry alerts. | Contract expectations linked. |
| SUP-FR-014 | 18 | Supplier change notification | Record supplier/manufacturer/process/material/site change notices and link to Change Control/impact assessment. | Supplier changes assessed. |
| SUP-FR-015 | 18 | Supplier performance | Track incoming acceptance, rejects, SCARs, complaints, deviations, delivery performance and quality metrics. | Requalification data driven. |
| SUP-FR-016 | 18 | SCAR initiation | Create supplier corrective-action request from incoming defect, deviation, audit or trend and track response/effectiveness. | QMS integration. |
| SUP-FR-017 | 18 | Material-source approval | Specific material/specification can have allowed supplier + manufacturer combinations and alternates. | Wrong source blocked. |
| SUP-FR-018 | 18 | Procurement item mapping | Map regulated material/spec version to purchasing description/code and ERP/native item without losing regulated identity. | Commercial/GxP identities separated. |
| SUP-FR-019 | 18 | Purchase requisition | Create PR with requesting site, material/spec version, quantity/UOM, need date, approved source requirements and project/batch reference if applicable. | Requirements exact. |
| SUP-FR-020 | 18 | PR approval | Configurable approval by amount/site/category plus quality gate for critical/unapproved source. | No buyer override. |
| SUP-FR-021 | 18 | RFQ | Optional RFQ to approved candidate suppliers, capturing commercial quote separately from qualification status. | Commercial comparison. |
| SUP-FR-022 | 18 | Supplier selection | Buyer may select only eligible supplier/manufacturer relationship unless controlled exception is approved. | ASL enforced. |
| SUP-FR-023 | 18 | Purchase order | PO includes exact regulated material/spec reference, supplier/manufacturer, quantity/UOM, delivery site and quality/document requirements. | Receipt expectations exact. |
| SUP-FR-024 | 18 | PO revision | Commercial changes versioned; regulated source/spec changes require revalidation/quality approval and may require new PO revision. | No silent source substitution. |
| SUP-FR-025 | 18 | COA/document requirement | PO may define required COA/CoC/test certificate/sterility certificate/document set. | Receipt completeness known. |
| SUP-FR-026 | 18 | Lot/document terms | PO can require supplier lot, manufacturer lot, manufacture/expiry/retest data and container identity information. | Traceability prepared. |
| SUP-FR-027 | 18 | ERP mode | If external ERP owns PR/RFQ/PO, eBMR receives validated references and enforces ASL/spec/source eligibility; ERP remains financial/commercial SoR. | Adapter boundary. |
| SUP-FR-028 | 18 | Native mode | If no ERP, native procurement supports PR/RFQ/PO and status without implementing GL/AP/tax settlement. | SME-ready. |
| SUP-FR-029 | 18 | Duplicate supplier detection | Detect likely duplicate legal/manufacturer identities before creation; merge prohibited without controlled data-management procedure. | Master quality. |
| SUP-FR-030 | 18 | Supplier document expiry | Alert certificates/agreements/audits nearing expiry and evaluate whether they affect eligibility. | No stale qualification. |
| SUP-FR-031 | 18 | Procurement audit | Audit source selection, approval, PO regulated-field changes, exceptions and external synchronization. | Traceable purchasing. |
| SUP-FR-032 | 18 | Inspection export | Provide supplier qualification/ASL/SCAR/audit/performance history for authorized review. | Inspection-ready. |
| RCV-FR-001 | 19 | Expected receipt | Load PO/transfer expectation with exact material/spec/source/quantity/document requirements. | Receiver knows expected material. |
| RCV-FR-002 | 19 | Receipt transaction | Create immutable receipt ID, site, date/time, receiver, carrier/reference, PO/source and received quantity. | Receipt attributable. |
| RCV-FR-003 | 19 | Visual examination | Capture appropriate labeling, damage, broken seals, contamination and shipment-condition observations before acceptance into quarantine. | 211.82-style receipt check. |
| RCV-FR-004 | 19 | Material identity | Match received material code/name/spec to expected material; mismatch creates hold/deviation, not silent remapping. | Wrong material blocked. |
| RCV-FR-005 | 19 | Supplier/manufacturer identity | Capture supplier and actual manufacturer and validate against approved source matrix. | Source eligibility checked. |
| RCV-FR-006 | 19 | Supplier lot | Capture supplier lot/batch number exactly as received. | Traceability. |
| RCV-FR-007 | 19 | Manufacturer lot | Capture manufacturer lot where distinct. | Source traceability. |
| RCV-FR-008 | 19 | Internal lot | Generate unique internal lot code for each received lot/shipment grouping according to site policy. | Distinctive status code. |
| RCV-FR-009 | 19 | Container identity | Create individual/container-group IDs and optional barcodes/QR labels. | Sampling/dispensing exact. |
| RCV-FR-010 | 19 | Quantity | Capture received gross/net/accepted quantity and UOM with conversion rules. | Inventory accurate. |
| RCV-FR-011 | 19 | Manufacture/expiry/retest | Capture available manufacture, expiry and retest dates with source/evidence and validation. | Eligibility later. |
| RCV-FR-012 | 19 | COA/CoC | Capture required documents, file hash, source and document completeness. | Supplier evidence linked. |
| RCV-FR-013 | 19 | COA extraction | AI/OCR may assist data entry later, but extracted data is advisory until verified; original document remains evidence. | No autonomous release. |
| RCV-FR-014 | 19 | Shipment conditions | Capture temperature logger/transport condition evidence where required and generate excursion if outside rule. | Cold-chain support. |
| RCV-FR-015 | 19 | Automatic quarantine | All applicable incoming regulated materials/containers/closures enter QUARANTINE by default until required test/examination and QC disposition. | No direct released receipt. |
| RCV-FR-016 | 19 | Physical/location quarantine | Assign allowed quarantine location/zone; system prevents issue/dispense from quarantined stock. | Status enforced. |
| RCV-FR-017 | 19 | Status label | Generate container/lot status label containing internal lot/container ID, material, status and other configured fields. | Physical/digital alignment. |
| RCV-FR-018 | 19 | Sampling request | Create sampling order based on material/spec/supplier risk/lot/shipment and sampling plan. | QC workflow initiated. |
| RCV-FR-019 | 19 | Container selection | Sampling plan identifies container(s) selected and quantity; actual selected containers recorded. | Representative sample trace. |
| RCV-FR-020 | 19 | Sampling execution | Capture sampler, date/time, method/procedure reference, container, sample ID and reseal/marking evidence. | 211.84-style evidence. |
| RCV-FR-021 | 19 | Aseptic sampling | Where required enforce sterile equipment/aseptic sampling qualification/profile and environment evidence. | Sterile materials supported. |
| RCV-FR-022 | 19 | Sample chain of custody | Track sample container/location/transfer to QC/LIMS and status. | Sample integrity. |
| RCV-FR-023 | 19 | Identity test | For applicable drug components require identity testing rule and result before release; supplier COA alone cannot bypass required identity testing. | 211.84 support. |
| RCV-FR-024 | 19 | Supplier COA reliance | Where permitted by profile, accept supplier analysis only with approved supplier-reliability status and required manufacturer testing/identity controls. | Conditional reliance. |
| RCV-FR-025 | 19 | Incoming QC | Link required tests/specification, native QC or LIMS results and result versions. | Disposition evidence. |
| RCV-FR-026 | 19 | Release disposition | Authorized Quality transitions lot/container group to RELEASED only after required evidence/rules complete. | QC authority. |
| RCV-FR-027 | 19 | Reject disposition | Failed lot becomes REJECTED and is controlled under segregated status/location to prevent use. | 211.89 support. |
| RCV-FR-028 | 19 | Conditional/under-deviation use | Default disabled; if customer procedure permits exceptional use, require deviation, quality approval, bounded scope and explicit material eligibility rule. | Exception controlled. |
| RCV-FR-029 | 19 | Retest status | Material may transition to RETEST_DUE/QUARANTINE and requires reexamination/retest before continued use where required. | 211.87 support. |
| RCV-FR-030 | 19 | Partial lot disposition | Allow container-level partial release/reject only when sampling/spec/profile explicitly permits and genealogy remains exact. | No ambiguous status. |
| RCV-FR-031 | 19 | Receipt discrepancy | Over/short/damaged/wrong lot/document mismatch generates discrepancy workflow and ERP reconciliation. | Commercial/GxP synchronized. |
| RCV-FR-032 | 19 | Audit/export | Full receipt→quarantine→sample→QC→release/reject history is exportable. | Inspection-ready. |
| INV-FR-001 | 20 | Warehouse master | Define site warehouse, zones, rooms, bins/locations, environmental class and permitted status/material categories. | Location controlled. |
| INV-FR-002 | 20 | Status segregation | Locations can be designated quarantine, released, rejected, return, destruction, controlled-temperature, sterile/component or other configured zones. | Physical/digital status aligned. |
| INV-FR-003 | 20 | Lot inventory | Maintain on-hand/reserved/available quantity by material lot and container. | Exact stock. |
| INV-FR-004 | 20 | Container inventory | Track individual container quantity/status/location where material handling requires it. | Dispensing source exact. |
| INV-FR-005 | 20 | Unit-of-measure | Canonical UOM and validated conversion used for stock transactions. | No unit ambiguity. |
| INV-FR-006 | 20 | Inventory transaction ledger | Every receipt, transfer, reserve, issue, dispense, consume, return, adjust, reject/destruct creates immutable transaction. | No editable balance. |
| INV-FR-007 | 20 | Derived balance | Current quantity derives from transaction ledger/projection and is reconciliation-tested. | History authoritative. |
| INV-FR-008 | 20 | Location transfer | Move lot/container between permitted locations with scanner/manual verification and status compatibility. | Wrong zone blocked. |
| INV-FR-009 | 20 | Inter-site transfer | Controlled shipment/receipt relationship preserving lot/container identity and quality state rules. | Multi-plant trace. |
| INV-FR-010 | 20 | Reservation | Reserve quantity/containers for batch/order without consuming; prevent over-reservation. | Planning safe. |
| INV-FR-011 | 20 | Reservation expiry/release | Reservation has status/expiry/cancel rules and can be released when batch changes. | No stranded stock. |
| INV-FR-012 | 20 | FEFO/FIFO policy | Selection engine prioritizes approved stock by product/profile rule; drug-side baseline supports oldest-approved stock rotation and deviation path. | Stock rotation compliant. |
| INV-FR-013 | 20 | Expiry | Expired material automatically becomes ineligible and may trigger status/hold workflow. | No expired use. |
| INV-FR-014 | 20 | Retest due | Retest-due material becomes ineligible/quarantine according to profile until reapproved. | 211.87 support. |
| INV-FR-015 | 20 | Quality hold | Quality can place lot/container hold independent of warehouse location. | Immediate block. |
| INV-FR-016 | 20 | Recall/blocked source | Supplier/material/quality event can block affected lots/containers through impact command. | Quality integrated. |
| INV-FR-017 | 20 | Product eligibility | Material lot may be released generally but only eligible for products/sites/spec versions defined by rules. | Correct product use. |
| INV-FR-018 | 20 | Alternative material | Selection of approved alternative material requires recipe/rule compatibility and possibly change/deviation approval. | No ad hoc substitution. |
| INV-FR-019 | 20 | Barcode | Generate/accept controlled barcode for material/lot/container/location; scan verifies expected identity. | Shop-floor reliability. |
| INV-FR-020 | 20 | Cycle count | Perform controlled inventory counts, discrepancies and adjustment approval without altering GxP transaction history. | Inventory accuracy. |
| INV-FR-021 | 20 | Physical count freeze | Optional location/item count lock prevents conflicting warehouse movements during count. | Concurrency safe. |
| INV-FR-022 | 20 | Negative inventory | GxP inventory cannot go negative through normal transaction. | Constraint. |
| INV-FR-023 | 20 | Container split | Split container creates child container identities with quantity conservation and parent relationship. | Traceability. |
| INV-FR-024 | 20 | Container merge | Merge only when material/spec/lot/status compatibility rules permit; preserve source relationships. | No identity loss. |
| INV-FR-025 | 20 | Partial container | Track remaining quantity after sampling/dispensing/return and reseal/open status where relevant. | Usability. |
| INV-FR-026 | 20 | Storage condition | Associate material/location storage requirements and environmental evidence/reference; excursion creates hold/impact when configured. | Quality protection. |
| INV-FR-027 | 20 | Label status | Container status labels reprinted only through controlled reprint with current quality status/version. | Physical status current. |
| INV-FR-028 | 20 | Inventory reconciliation with ERP | Compare GxP quantity to ERP/WMS quantity/reference; mismatches flagged, never auto-resolved by overwriting GxP ledger. | Boundary. |
| INV-FR-029 | 20 | Search | Search stock by material/spec/lot/container/status/location/expiry/retest/supplier/manufacturer. | Operational. |
| INV-FR-030 | 20 | Genealogy | Inventory transactions create/maintain lot/container provenance used by Document 13. | Traceable. |
| INV-FR-031 | 20 | Retention | Transaction history retained according to associated regulated record/material policy. | Evidence enduring. |
| INV-FR-032 | 20 | Performance | Support thousands/millions of inventory transactions with indexed ledger and balance projection. | Enterprise scale. |
| DSP-FR-001 | 21 | Dispensing order | Create dispensing requirement from issued batch recipe snapshot with material spec, target quantity/formula, tolerance, stage and batch. | Exact demand. |
| DSP-FR-002 | 21 | Candidate selection | Suggest eligible released lots/containers using Inventory selection rules; operator cannot select excluded lot. | Wrong material prevented. |
| DSP-FR-003 | 21 | Material scan | Require material/lot/container barcode scan where configured and verify against requirement. | Identity check. |
| DSP-FR-004 | 21 | Location scan | Optionally verify warehouse/dispensing booth/location before operation. | Context. |
| DSP-FR-005 | 21 | Operator qualification | Require active dispensing qualification/training and site access. | Qualified personnel. |
| DSP-FR-006 | 21 | Balance eligibility | Verify balance/device registration, calibration, qualification, location and status before use. | Valid equipment. |
| DSP-FR-007 | 21 | Tare | Capture tare method/value/container and device source where applicable. | Net weight reproducible. |
| DSP-FR-008 | 21 | Target quantity | Target from recipe calculation, including potency adjustment where configured; exact rule version retained. | No manual target change. |
| DSP-FR-009 | 21 | Live balance capture | Read stable weight from Edge/Balance adapter with device identity, timestamp and quality. | Automated evidence. |
| DSP-FR-010 | 21 | Stability rule | Balance adapter/config defines stable-reading criteria and unit/precision. | No transient reading. |
| DSP-FR-011 | 21 | Manual weight fallback | Allowed only when recipe/device fallback policy permits; requires reason, manual source, possibly independent verification/signature. | Controlled fallback. |
| DSP-FR-012 | 21 | Tolerance | Evaluate actual against released tolerance rule; outside tolerance blocks completion/creates exception. | Correct quantity. |
| DSP-FR-013 | 21 | Multiple additions | Support incremental weigh additions while preserving readings and final accepted net. | Full history. |
| DSP-FR-014 | 21 | Overweight correction | If allowed, controlled removal/reweigh records all readings and material disposition; original overweight reading retained. | No overwrite. |
| DSP-FR-015 | 21 | Underweight correction | Additional material can be added from same/allowed lot according to policy; each addition traceable. | Accurate genealogy. |
| DSP-FR-016 | 21 | Potency adjustment | Use released assay/potency result and rule to determine active material target; verifier sees source and calculation. | Drug support. |
| DSP-FR-017 | 21 | Multi-lot dispensing | Use multiple approved lots only when recipe/profile permits; genealogy records each exact quantity. | No hidden pooling. |
| DSP-FR-018 | 21 | Independent verification | Support verifier scan/check of material/lot/target/actual/device and e-signature where required. | Second-person check. |
| DSP-FR-019 | 21 | Dispensed container | Create dispensed-material container/package identity with label and exact source lot/container quantities. | Shop-floor trace. |
| DSP-FR-020 | 21 | Dispensing label | Print controlled label including material, batch, dispensed qty/UOM, source lot(s), date/time, status, expiry/use-by if configured. | Identity maintained. |
| DSP-FR-021 | 21 | Label reprint | Controlled reprint with reason and count/history. | No uncontrolled duplicates. |
| DSP-FR-022 | 21 | Material issue | On accepted dispense, post inventory transaction/reservation consumption for exact source quantity. | Stock consistent. |
| DSP-FR-023 | 21 | Genealogy | Create source lot/container → dispensed container → batch relationship. | Trace. |
| DSP-FR-024 | 21 | Partial source container | Update remaining source-container quantity and open/reseal status. | Inventory correct. |
| DSP-FR-025 | 21 | Expiry/retest recheck | Revalidate source lot at dispense completion, not only initial selection, for long operations. | No stale eligibility. |
| DSP-FR-026 | 21 | Environmental/booth condition | Where required verify dispensing area/environment status before operation. | Controlled environment. |
| DSP-FR-027 | 21 | Line/booth clearance | Require applicable booth/area clearance status before dispensing. | Cross-contamination prevention. |
| DSP-FR-028 | 21 | Exception | Wrong scan, ineligible lot, balance failure, tolerance failure, qualification lapse or environment issue creates/block according to rule. | Fail safe. |
| DSP-FR-029 | 21 | Pause/resume | Preserve in-progress readings; resume revalidates material/balance/operator/status according to policy. | Interrupted work safe. |
| DSP-FR-030 | 21 | Cancel | Cancel before completion returns reservation and retains attempted evidence/reason; no consumption posted unless physically handled per policy. | No lost trace. |
| DSP-FR-031 | 21 | Bulk dispensing | Support batch/staged dispensing queue but each requirement has independent identity, eligibility, weight and genealogy. | Efficiency without ambiguity. |
| DSP-FR-032 | 21 | Audit/export | Dispensing record includes target/calculation, source lots, all relevant readings, actual, equipment, operators/verifier, signatures, labels and exceptions. | eBMR evidence complete. |
| CON-FR-001 | 22 | Issue to production | Move dispensed/material container to production staging/use with exact batch/step reference and status. | Custody trace. |
| CON-FR-002 | 22 | Consumption | Record actual material quantity consumed in step, source dispensed container/lot and time. | Actual use evidence. |
| CON-FR-003 | 22 | Automatic consumption | Where machine/process provides authoritative quantity, accept via validated integration/rule; otherwise controlled manual capture. | Flexible source. |
| CON-FR-004 | 22 | Partial consumption | Track remaining quantity in dispensed container and resulting status/location. | No assumed full use. |
| CON-FR-005 | 22 | Return to warehouse | Return unused eligible material with quantity, seal/container condition, storage condition and status reevaluation. | Safe return. |
| CON-FR-006 | 22 | Return rejection | If return condition unsuitable, route to quarantine/reject/destruction workflow rather than normal stock. | No bad return. |
| CON-FR-007 | 22 | Material re-status after return | Product/profile may require QC/QA evaluation after exposure/opening/temperature excursion before reuse. | Risk controlled. |
| CON-FR-008 | 22 | Excess material | Record excess generated/remaining from dispensing/process and controlled disposition. | Balance complete. |
| CON-FR-009 | 22 | Process loss | Record allowed loss category/quantity/source and approval/rule. | Variance explained. |
| CON-FR-010 | 22 | Spill | Record spill quantity/estimate, quality/deviation link and cleanup evidence where required. | Incident trace. |
| CON-FR-011 | 22 | Sample withdrawal | Account for QC/in-process/reserve sample quantity and sample ID. | Balance. |
| CON-FR-012 | 22 | Reject/scrap material | Record rejected process material quantity, reason, location and disposition. | No ghost stock. |
| CON-FR-013 | 22 | Inventory adjustment | Exceptional positive/negative adjustment requires controlled reason, evidence, authorization and audit; cannot be routine correction for software defects. | Controlled discrepancy. |
| CON-FR-014 | 22 | Adjustment SoD | High-risk adjustment can require independent approval; user cannot approve own adjustment if configured. | Fraud/error control. |
| CON-FR-015 | 22 | Destruction request | Create destruction disposition for rejected/expired/excess/material/product with exact lot/container/quantity. | Scope exact. |
| CON-FR-016 | 22 | Destruction authorization | Require QA/authorized approval and witness where policy requires. | Controlled disposition. |
| CON-FR-017 | 22 | Destruction execution | Record method, date/time, performers/witnesses, quantity, evidence and destination/vendor where applicable. | Evidence. |
| CON-FR-018 | 22 | Third-party destruction | Track approved vendor/manifest/certificate and chain of custody. | External disposition trace. |
| CON-FR-019 | 22 | Reconciliation scope | Calculate material balance by batch/material requirement/lot/container/stage according to released rules. | Configurable scope. |
| CON-FR-020 | 22 | Source categories | Reconciliation includes dispensed/issued, consumed, returned, samples, rejected, destroyed, approved loss and unexplained variance. | Complete mass balance. |
| CON-FR-021 | 22 | Tolerance | Use Document 08/17 released tolerance/rounding/UOM rules. | Deterministic. |
| CON-FR-022 | 22 | Variance blocker | Out-of-tolerance/unexplained variance creates deviation/investigation and blocks production completion/release as configured. | No silent loss. |
| CON-FR-023 | 22 | Correction recalculation | Any corrected transaction creates superseding transaction/event and automatically recalculates affected reconciliation; original remains. | History. |
| CON-FR-024 | 22 | No transaction deletion | Consumption/return/adjustment/destruction records are immutable transactions; correction is reversal/supersession pattern. | Ledger integrity. |
| CON-FR-025 | 22 | ERP posting | Post consumption/return/scrap/destruction quantity/reference after GxP commit; retries idempotent. | Commercial sync. |
| CON-FR-026 | 22 | ERP discrepancy | Compare external postings and create reconciliation issue; ERP never overwrites GxP transaction ledger. | Boundary. |
| CON-FR-027 | 22 | Genealogy impact | Consumption creates genealogy; return/destruction preserves source/material identity and affected batch links. | Trace. |
| CON-FR-028 | 22 | Batch completion gate | All required material transactions/reconciliation must be current/acceptable before Production Complete. | eBMR complete. |
| CON-FR-029 | 22 | QA review | Review-by-exception shows adjustments, spills, losses, destruction and failed reconciliation. | Quality visibility. |
| CON-FR-030 | 22 | Audit/export | Batch/material history export includes all source/quantity/disposition/reconciliation records and signatures. | Inspection-ready. |
| CON-FR-031 | 22 | Cross-batch prohibition | A dispensed container assigned to Batch A cannot be consumed in Batch B unless a controlled return/reissue process creates new authorization. | No cross-use. |
| CON-FR-032 | 22 | Performance | Batch reconciliation may aggregate large device/packaging/component transaction sets asynchronously but current status is versioned. | Scale safe. |
| QC-FR-001 | 23 | Test specification master | Create versioned test specification by material/product/in-process/device scope with test list, methods, acceptance criteria, sampling plan and release dependency. | QC requirement controlled. |
| QC-FR-002 | 23 | Specification lifecycle | Draft, review, released/effective, superseded, obsolete, suspended; released spec immutable and Vault-backed. | No live edit. |
| QC-FR-003 | 23 | Test method reference | Each test references approved method/version, compendial/internal/validated method type and suitability/validation evidence reference. | Method exact. |
| QC-FR-004 | 23 | Method modification | Modified method requires controlled version, reason, validation/suitability evidence and approval; original method remains. | 211.194(b)-style record support. |
| QC-FR-005 | 23 | Sampling plan | Define sample source, quantity, number of units/containers, selection rule, frequency, sample type and reserve/retain behavior. | Written sampling plan. |
| QC-FR-006 | 23 | Sample identity | Assign immutable sample ID linked to source lot/batch/container/unit/location, amount, date sampled and date received in lab. | 211.194 sample identity. |
| QC-FR-007 | 23 | Sample type | Support incoming, in-process, finished product, device test, environmental, stability, reserve/retain and investigation samples. | Common QC core. |
| QC-FR-008 | 23 | Sampling execution | Record sampler, procedure/version, source location/container, amount, timestamp, container/label and chain-of-custody start. | Sample attributable. |
| QC-FR-009 | 23 | Chain of custody | Track sample transfers, lab location, storage condition, aliquots, destruction/retain status and custodians. | Sample integrity. |
| QC-FR-010 | 23 | Test order | Create one or more test orders from sample/spec with required tests, priority, due date and release/blocking flags. | Work queue controlled. |
| QC-FR-011 | 23 | Analyst assignment | Assign qualified analyst/team; qualification/training and method authorization checked at execution. | Qualified lab personnel. |
| QC-FR-012 | 23 | Instrument eligibility | Verify instrument/test equipment ID, calibration/status/method compatibility before accepting instrument-generated result. | Unqualified instrument blocked. |
| QC-FR-013 | 23 | Reference standard/reagent | Capture reference standard, reagent/solution IDs, lot, expiry/standardization status where test requires them. | Laboratory records complete. |
| QC-FR-014 | 23 | Sample amount | Record weight/measure used for each test where applicable. | 211.194(a)(3) support. |
| QC-FR-015 | 23 | Raw data | Retain all required raw data or immutable evidence references, including graphs/charts/spectra/files where produced by instrument. | Complete data. |
| QC-FR-016 | 23 | Manual raw data | Structured manual observations/entries capture analyst/time/unit/method step and audit history. | No untraceable worksheet. |
| QC-FR-017 | 23 | Instrument raw data | Instrument integration stores source ID, original file/reference, sequence/run ID, acquisition time, hash and metadata. | Original data preserved. |
| QC-FR-018 | 23 | Calculations | Use released calculation rules for calculations, units, conversion/equivalency factors and rounding; persist inputs/results/version. | 211.194(a)(5) support. |
| QC-FR-019 | 23 | Result | Store structured result, unit, method/spec version, acceptance criterion and Pass/Fail/OOS/OOT/Pending status. | Result meaning explicit. |
| QC-FR-020 | 23 | Multiple determinations | Model replicates/injections/readings individually where method requires; final reported result derives via released method/rule. | No hidden averaging. |
| QC-FR-021 | 23 | System suitability | Where applicable record system-suitability checks separately and determine whether test run is valid under method. | Invalid test distinguished. |
| QC-FR-022 | 23 | Analyst completion | Analyst signs/completes test record after all required data/results/evidence present. | Performer attribution. |
| QC-FR-023 | 23 | Second-person review | Reviewer verifies original records for accuracy, completeness and specification compliance; controlled e-sign where Part 11 applies. | 211.194(a)(8) support. |
| QC-FR-024 | 23 | Result correction | Correction creates superseding result/version with reason; original remains visible and may trigger impact review. | No overwrite. |
| QC-FR-025 | 23 | OOS trigger | Any applicable result outside specification/acceptance criteria automatically creates OOS candidate/record; user cannot suppress trigger. | Failed result preserved. |
| QC-FR-026 | 23 | OOT trigger | Released trend rule may flag result as OOT even if within specification; create OOT record without changing raw result. | Trend signal. |
| QC-FR-027 | 23 | Invalid test | Test may be invalidated only through controlled investigation with assignable cause/evidence; invalidation does not delete raw data. | Scientific invalidation. |
| QC-FR-028 | 23 | Retest | Retest cannot be started merely by editing/re-running failed result; it requires OOS/investigation authorization and new test instance. | No testing into compliance. |
| QC-FR-029 | 23 | Resample | New sample after OOS requires controlled authorization and scientific rationale; linked to original sample/OOS. | Controlled resampling. |
| QC-FR-030 | 23 | Material/batch disposition | QC test-set completion updates quality/release readiness but does not directly perform final batch/material release unless authorized module command executes. | Authority separated. |
| QC-FR-031 | 23 | Partial test completion | Test order shows incomplete required tests and blocks dependent release/step. | No false completion. |
| QC-FR-032 | 23 | Microbiology result support | Support qualitative/count results, incubation periods, organism/reference metadata and delayed completion without forcing all tests into numeric schema. | Future pharma/sterile ready. |
| QC-FR-033 | 23 | Device test support | Support force, torque, dimensional, dose-delivery, leak, electrical/functional, visual or other structured device test result types. | DDCP/device ready. |
| QC-FR-034 | 23 | Attachment/evidence | Attach method worksheets, chromatograms, spectra, reports, images and certificates with hash/version/source metadata. | Evidence complete. |
| QC-FR-035 | 23 | Stability linkage | Architecture can tag stability sample/timepoint/study and retain results, while full Stability Management may be separate later spec. | Expandable. |
| QC-FR-036 | 23 | QC dashboard | Show samples/tests by status, overdue, OOS/OOT, analyst, instrument, product/material and release blockers. | Operational. |
| QC-FR-037 | 23 | Search/export | Authorized users can retrieve complete sample/test record including raw data refs, calculations, analyst/reviewer signatures and audit. | Inspection-ready. |
| QC-FR-038 | 23 | No deletion | Sample/test/result/raw-data metadata cannot be physically deleted by normal application workflow. | Data integrity. |
| LIMS-FR-001 | 24 | Provider abstraction | Expose generic LIMSProvider contract independent of LabWare/STARLIMS/openBIS/custom vendor. | Vendor-neutral domain. |
| LIMS-FR-002 | 24 | System registry | Register LIMS instances, site scope, auth method, endpoint/version, supported operations and health. | Multiple LIMS supported. |
| LIMS-FR-003 | 24 | Master mapping | Map product/material/test method/spec/sample types and external IDs with version/status. | Semantic mapping controlled. |
| LIMS-FR-004 | 24 | Sample creation | Send sample/test request with exact source record/version, required tests, priority and correlation ID. | Request attributable. |
| LIMS-FR-005 | 24 | External sample ID | Persist LIMS sample/order IDs without replacing internal GxP IDs. | Identity separation. |
| LIMS-FR-006 | 24 | Status sync | Receive/poll sample/test statuses using idempotent versioned callbacks. | Workflow current. |
| LIMS-FR-007 | 24 | Result ingestion | Receive structured result including test code, value/UOM, method, analyst/system source, completion/review state and external result version. | Complete result contract. |
| LIMS-FR-008 | 24 | Raw evidence reference | Receive secure evidence/file/export/reference metadata where integration design supports it. | Original evidence linked. |
| LIMS-FR-009 | 24 | Result versioning | Each LIMS result/revision maps to immutable accepted GxP result version; original prior versions retained. | No overwrite. |
| LIMS-FR-010 | 24 | Duplicate protection | Use external event/result IDs plus idempotency hash to avoid duplicate accepted results. | Replay safe. |
| LIMS-FR-011 | 24 | Ordering | Handle late/out-of-order callbacks by external version/sequence and current GxP state rules. | No stale overwrite. |
| LIMS-FR-012 | 24 | Schema validation | Validate required fields, data types, UOM, test mapping, method version and source identity before acceptance. | Bad payload rejected/quarantined. |
| LIMS-FR-013 | 24 | Source authentication | Use mTLS/OAuth/workload identity/API signing as supported; anonymous callbacks prohibited. | Trusted source. |
| LIMS-FR-014 | 24 | Tenant/site scope | LIMS instance and mapping restricted to authorized customer/site. | Isolation. |
| LIMS-FR-015 | 24 | Result acceptance policy | External LIMS 'approved' status is evidence, not automatic final batch release; GxP Release Engine evaluates overall eligibility. | Authority separated. |
| LIMS-FR-016 | 24 | OOS trigger | External OOS result creates/links GxP OOS record even if LIMS manages its own investigation; source-of-truth responsibility is configured. | No missed OOS. |
| LIMS-FR-017 | 24 | OOS ownership mode | Support GXP_MANAGED, LIMS_MANAGED_WITH_SYNC, or HYBRID integration profile with explicit field/state ownership. | No dual-master conflict. |
| LIMS-FR-018 | 24 | OOT sync | Receive OOT/trend flag where external LIMS provides it; GxP may independently evaluate configured OOT rules. | Trend visible. |
| LIMS-FR-019 | 24 | Result correction | LIMS revision creates new accepted version; never update prior GxP result row. | Data integrity. |
| LIMS-FR-020 | 24 | Retest/resample linkage | External new test/sample must carry relation to originating OOS/investigation when applicable. | Scientific history preserved. |
| LIMS-FR-021 | 24 | Cancellation | Sample/test cancellation requires reason/source and may be blocked if required for batch/material release. | No silent missing test. |
| LIMS-FR-022 | 24 | Acknowledgement | GxP sends accepted/rejected callback acknowledgement with internal event/result ID. | Reconciliation. |
| LIMS-FR-023 | 24 | Retry | Outbound and inbound processing idempotent with exponential backoff and dead-letter/manual reconciliation. | Resilient. |
| LIMS-FR-024 | 24 | Dead letter | Unprocessable messages retained with payload hash/reference, error code, retry history and operator action. | No lost result. |
| LIMS-FR-025 | 24 | Reconciliation job | Periodically compare expected samples/tests/results between systems and surface missing/duplicate/version mismatch. | Integration integrity. |
| LIMS-FR-026 | 24 | Manual reconciliation | Authorized integration admin can map/replay/correct integration metadata, but cannot fabricate/change laboratory result. | Admin boundary. |
| LIMS-FR-027 | 24 | Time semantics | Store LIMS source timestamps and GxP received/accepted timestamps separately. | Chronology clear. |
| LIMS-FR-028 | 24 | Unit conversion | Only controlled UOM mapping/conversion; incompatible unit rejects result. | No semantic drift. |
| LIMS-FR-029 | 24 | Method mapping | Unknown/mismatched method/version is rejected/held for review rather than accepted as equivalent. | Method integrity. |
| LIMS-FR-030 | 24 | Attachment security | Files scanned, hashed and content-type validated; external URLs not treated as permanent evidence unless approved architecture preserves accessibility/integrity. | Evidence durable. |
| LIMS-FR-031 | 24 | Audit | Audit outbound request, inbound event, validation decision, accepted result version, mapping change and manual reconciliation. | Traceable. |
| LIMS-FR-032 | 24 | Monitoring | Health, queue age, error rate, last successful sync, result latency and reconciliation differences exposed. | Operational. |
| LIMS-FR-033 | 24 | Adapter versioning | Adapter and contract version recorded with each accepted result/event where needed for investigation. | Historical reproducibility. |
| LIMS-FR-034 | 24 | Test environment | Provide sandbox/simulator and contract test suite so vendor adapters can be validated before production. | Implementation safe. |
| OOS-FR-001 | 25 | Automatic OOS creation | Applicable result outside released specification/acceptance criterion creates OOS record automatically and links original result/sample/test/batch/material. | OOS cannot be suppressed. |
| OOS-FR-002 | 25 | Original result preservation | Original result, raw data, calculations, method, analyst, instrument, timestamps and audit remain immutable/retrievable regardless of later investigation/retest. | No result substitution. |
| OOS-FR-003 | 25 | Immediate notification | Notify QC/QA and affected batch/material workflow according to severity/profile; place release/continuation hold where configured. | Risk contained. |
| OOS-FR-004 | 25 | OOS state model | Open → Laboratory Investigation → Extended/Manufacturing Investigation if required → Impact/Disposition → QA Approval → Closed. | Controlled progression. |
| OOS-FR-005 | 25 | Phase I laboratory review | Capture analyst interview/check, method/procedure adherence, calculations, instrument status, standards/reagents, sample preparation, system suitability, raw data and obvious assignable cause evidence | Scientific initial investigation. |
| OOS-FR-006 | 25 | Assignable cause | Only invalidate original test as analytically invalid when documented evidence supports specific assignable laboratory cause under procedure. | No speculative invalidation. |
| OOS-FR-007 | 25 | No assignable cause | If no conclusive laboratory error, proceed to broader investigation rather than declaring test invalid. | Comprehensive investigation. |
| OOS-FR-008 | 25 | Manufacturing investigation | Link batch records, process parameters, materials, equipment, environment, deviations, other batches/lots and historical trends as required. | Root cause beyond lab. |
| OOS-FR-009 | 25 | Batch/material hold | OOS can place affected batch/material/related lots on controlled hold pending investigation. | No release. |
| OOS-FR-010 | 25 | Retest plan | Retesting requires predefined/procedurally justified number of retests, method, analyst/instrument strategy and interpretation rule approved before executing retest. | No testing into compliance. |
| OOS-FR-011 | 25 | Retest authorization | Authorized QC/QA approval required before retest; original test remains. | Controlled action. |
| OOS-FR-012 | 25 | Retest result | Each retest is independent test instance linked to OOS, with complete raw data/result/review. | Full evidence. |
| OOS-FR-013 | 25 | Retest interpretation | System does not automatically average away/replace initial OOS; outcome follows released OOS procedure/rule and QA disposition. | No cherry-picking. |
| OOS-FR-014 | 25 | Resample plan | Resampling requires scientific rationale that original sample may not represent batch/material, authorization and defined sampling plan. | Controlled resampling. |
| OOS-FR-015 | 25 | Resample lineage | New sample explicitly links to original sample/OOS and captures source/location/container/quantity/time. | Trace. |
| OOS-FR-016 | 25 | Invalid test classification | Invalid result/test remains visible with reason/evidence and state; does not become deleted/hidden. | Data integrity. |
| OOS-FR-017 | 25 | Root cause | Capture root cause category/method/evidence; “unknown/no assignable cause” allowed when justified, not forced fake cause. | Scientific integrity. |
| OOS-FR-018 | 25 | Impact assessment | Assess affected batch/material/product, related lots, prior/subsequent batches, stability/complaints/other results as procedure requires. | Scope determined. |
| OOS-FR-019 | 25 | Disposition | Possible outcomes include Confirmed OOS/Reject, Laboratory Error/Invalid Test, Manufacturing Cause, No Assignable Cause with QA decision, Reprocess/Rework path where allowed. | Explicit conclusion. |
| OOS-FR-020 | 25 | CAPA link | Create/link CAPA when investigation identifies systemic/corrective/preventive action need. | QMS integration. |
| OOS-FR-021 | 25 | Change control link | Method/process/spec/system changes resulting from OOS require controlled Change Control. | No informal fix. |
| OOS-FR-022 | 25 | Closure | OOS closes only after required investigation, impact, retest/resample dispositions, linked actions and QA approval/signature complete. | No premature closure. |
| OOS-FR-023 | 25 | Reopen | New material information/evidence can reopen closed OOS through controlled workflow preserving prior closure decision. | History. |
| OOT-FR-001 | 25 | OOT rule | Define versioned trend rule by test/product/material/site using statistical/historical/business methodology approved by customer Quality. | Configurable. |
| OOT-FR-002 | 25 | OOT trigger | Result can trigger OOT while still within specification; raw result remains PASS against specification plus separate OOT flag/investigation status. | Do not mislabel as OOS. |
| OOT-FR-003 | 25 | OOT baseline | Trend rule references approved historical window/population, expected range/control logic and exclusions. | Method reproducible. |
| OOT-FR-004 | 25 | OOT state model | Open → Trend Review → Investigation/Impact → Action/Disposition → QA Approval → Closed. | Controlled. |
| OOT-FR-005 | 25 | Historical comparison | Display current result versus prior lots/batches/timepoints and relevant statistics/limits without changing official result. | Context. |
| OOT-FR-006 | 25 | OOT impact | Determine potential effect on batch/material/stability/process and whether release hold is required by profile. | Risk based. |
| OOT-FR-007 | 25 | Repeat OOT escalation | Repeated OOT signals can escalate severity/CAPA/change review according to trend rules. | Systemic detection. |
| OOT-FR-008 | 25 | Spec vs trend separation | Specification acceptance and OOT trending are separate dimensions; one does not silently modify the other. | Semantics clear. |
| OOT-FR-009 | 25 | External trend source | External LIMS/statistical tool OOT flag may be imported with source/method/version; GxP retains accepted flag/investigation linkage. | Integration. |
| OOT-FR-010 | 25 | Trend recalculation | When baseline/rule changes, historical official results remain; new trend analyses are versioned rather than rewriting past OOT decisions. | History. |
| OOS-FR-024 | 25 | Role/SoD | Analyst, investigator, QC reviewer and QA approver permissions configurable; analyst cannot unilaterally invalidate own failing result. | Independent authority. |
| OOS-FR-025 | 25 | E-signature | Key investigation/authorization/closure/disposition actions use regulated signatures per policy. | Attributable decisions. |
| OOS-FR-026 | 25 | Audit | Every investigation statement, classification, retest/resample authorization, result, conclusion, impact and closure is auditable/versioned. | Inspection-ready. |
| OOS-FR-027 | 25 | Review-by-exception | Open/closed OOS/OOT, retests, invalidated tests and impact status appear in QA Review package. | Release aware. |
| OOS-FR-028 | 25 | Release engine | Open/unresolved/confirmed OOS/OOT impacts feed explicit release blockers/warnings based on profile. | No bypass. |
| OOS-FR-029 | 25 | Metrics/trending | Dashboard OOS rate, recurring test/method/instrument/product/analyst patterns and closure aging; metrics never substitute investigation. | Quality intelligence. |
| OOS-FR-030 | 25 | Export | Generate complete investigation package with original and all subsequent data/results, approvals, impacts, audit and linked CAPA/change. | Inspection-ready. |
