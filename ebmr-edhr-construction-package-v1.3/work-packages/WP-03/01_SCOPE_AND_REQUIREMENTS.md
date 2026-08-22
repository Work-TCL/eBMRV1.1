# WP-03 — Scope & Requirements

**In scope:** Documents 13, 14, 15, 16, 17

## Document 13 — Genealogy & Traceability Engine Specification (SPEC-EBMR-004)

- Code location: `services/gxp-api/src/modules/ebmr`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: GEN-FR-001..030 (30)

## Document 14 — Review-by-Exception & QA Review Specification (SPEC-EBMR-005)

- Code location: `services/gxp-api/src/modules/ebmr`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: RBE-FR-001..030 (30)

## Document 15 — Release / Disposition Engine Specification (SPEC-EBMR-006)

- Code location: `services/gxp-api/src/modules/ebmr`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: REL-FR-001..032 (32)

## Document 16 — Packaging, Labeling & Reconciliation Specification (SPEC-EBMR-007)

- Code location: `services/gxp-api/src/modules/ebmr`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: PKG-FR-001..032 (32)

## Document 17 — Yield, Calculations & Manufacturing Reconciliation Specification (SPEC-EBMR-008)

- Code location: `services/gxp-api/src/modules/ebmr`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: YLD-FR-001..032 (32)

## All requirements

| ID | Doc | Requirement | Behaviour | Acceptance |
|---|---|---|---|---|
| GEN-FR-001 | 13 | Canonical genealogy entity | Represent supplier/material lot/container, drug batch, intermediate, device component lot/serial, device unit, combination lot/serial, package and distribution reference as typed genealogy nodes. | Common trace model. |
| GEN-FR-002 | 13 | Typed relationships | Use controlled edge types such as CONTAINS, DERIVED_FROM, CONSUMED_IN, ASSEMBLED_INTO, PACKAGED_AS, FILLED_INTO, TESTED_BY, STERILIZED_IN, DISTRIBUTED_AS. | Meaning explicit. |
| GEN-FR-003 | 13 | Forward trace | Given source material/component/drug batch, return all directly/indirectly affected intermediates/final lots/serials/packages. | Recall impact. |
| GEN-FR-004 | 13 | Backward trace | Given final lot/serial, return all source materials/components/drug/device lots, operations and equipment evidence. | Investigation. |
| GEN-FR-005 | 13 | Container-level trace | Track internal material container identity where dispensing/partial use matters. | Exact source. |
| GEN-FR-006 | 13 | Quantity on edge | Store consumed/produced quantity + UOM for material transformation relationships where applicable. | Mass/quantity genealogy. |
| GEN-FR-007 | 13 | Step provenance | Edge can reference batch step/operation that created relationship. | Process context. |
| GEN-FR-008 | 13 | Version/hash provenance | Node/edge references exact authoritative record/version and source event. | No mutable pointer. |
| GEN-FR-009 | 13 | Drug-device compatibility | Final DDCP genealogy records exact constituent compatibility version used. | Pairing evidence. |
| GEN-FR-010 | 13 | Serial relationship | Support component serial → device serial → combination-product serial. | Unit trace. |
| GEN-FR-011 | 13 | Lot-to-serial scale | Efficiently represent many serials consuming same lot without unbounded duplicated metadata. | Scale. |
| GEN-FR-012 | 13 | Package hierarchy | Represent unit → carton → shipper/pallet/package aggregation where required. | Distribution/recall. |
| GEN-FR-013 | 13 | Distribution reference | Link released product lot/serial/package to ERP/WMS shipment/distribution reference without making ERP record genealogy truth. | Downstream trace. |
| GEN-FR-014 | 13 | Rework relationship | Record REWORKED_FROM/SUPERSEDES relationships preserving original identity. | History. |
| GEN-FR-015 | 13 | Split/merge | Support one lot split into many, many materials into one batch, subassemblies merged into final unit. | Manufacturing transformations. |
| GEN-FR-016 | 13 | No arbitrary deletion | Genealogy nodes/edges from regulated execution are immutable facts; corrections append superseding/voiding relationship metadata. | Trace cannot disappear. |
| GEN-FR-017 | 13 | Correction | If erroneous link was recorded, correction marks original as invalid/superseded through controlled event and adds correct edge; original remains. | Audit. |
| GEN-FR-018 | 13 | Recall query | Query affected final products, inventory, released/distributed references and quality events from any source node. | Field action support. |
| GEN-FR-019 | 13 | Complaint query | Serial/lot complaint query retrieves full manufacturing/constituent history and related prior complaints/events. | Investigation. |
| GEN-FR-020 | 13 | Supplier impact | Supplier/manufacturer lot can identify internal lots and finished product impact. | Supplier quality. |
| GEN-FR-021 | 13 | Equipment correlation | Optionally associate operations with actual equipment, but do not model equipment as material ancestry unless semantically appropriate. | Process evidence. |
| GEN-FR-022 | 13 | Evidence links | Node/edge can reference COA, test report, assembly/test evidence, sterilization evidence. | Complete context. |
| GEN-FR-023 | 13 | Graph consistency | Prevent invalid edge classes, self-relationships, impossible product type transitions and duplicate exact edges. | Semantic integrity. |
| GEN-FR-024 | 13 | Cycle handling | Material/product ancestry should normally be acyclic; rework/correction relationships are separately typed to avoid misleading ancestry cycles. | Trace algorithm safe. |
| GEN-FR-025 | 13 | Traversal depth | Support bounded/unbounded authorized traversals with protection against runaway queries. | Performance/security. |
| GEN-FR-026 | 13 | Affected scope snapshot | Recall/impact assessment can save a versioned result set with query criteria, graph version/cutoff and reviewer signature. | Investigation reproducible. |
| GEN-FR-027 | 13 | External mapping | ERP/LIMS source IDs linked to nodes as provenance but internal genealogy IDs remain authoritative. | Vendor independence. |
| GEN-FR-028 | 13 | Import/migration | Migrated genealogy identifies source system/migration batch and preserves source checksum. | Historical provenance. |
| GEN-FR-029 | 13 | Performance | Target common single-serial backward trace under interactive latency and large-lot forward impact through indexed traversal/materialized helper tables. | Usable at scale. |
| GEN-FR-030 | 13 | Export | Generate structured genealogy JSON/CSV and human-readable trace report with node/edge evidence. | Inspection/recall ready. |
| RBE-FR-001 | 14 | Review package | At Production Complete create versioned QA review package referencing stable batch record version and current exception index. | QA reviews defined scope. |
| RBE-FR-002 | 14 | Full-record access | Review-by-exception is an aid, not a substitute for access to complete record/evidence. | No hidden record. |
| RBE-FR-003 | 14 | Exception index | Aggregate deviations, OOS/OOT, NCRs, parameter excursions, manual overrides, corrections, missing evidence, failed integrations, late steps, equipment/material/environment issues, reconciliation/yield | Critical issues visible. |
| RBE-FR-004 | 14 | Severity | Assign severity/risk/category using released rule/QMS classification; QA may reclassify only through controlled reason/authority. | Prioritization controlled. |
| RBE-FR-005 | 14 | Completeness engine | Independently verify all applicable steps, required values, evidence, signatures, QC, materials, genealogy and calculations are present. | Missing data cannot be hidden because no exception was generated. |
| RBE-FR-006 | 14 | Changed-value review | List every controlled correction/superseded value with old/new, reason, actor, signature and impact. | Corrections obvious. |
| RBE-FR-007 | 14 | Manual override review | List automated-to-manual fallback, overrides, waived checks and exceptional authorizations. | Non-routine activity visible. |
| RBE-FR-008 | 14 | Audit-trail review | Provide filtered audit view for critical records/fields and allow QA to document review status separately. | Part 11/data-integrity support. |
| RBE-FR-009 | 14 | Signature review | Check required signatures exist, are valid, bound to current versions and satisfy SoD. | No invalid signature chain. |
| RBE-FR-010 | 14 | QC review | Summarize required tests, accepted results, superseded results, OOS/OOT and pending items. | QC status clear. |
| RBE-FR-011 | 14 | Material review | Summarize material lots, quality status at use, deviations, substitutions, reconciliation and expired/retest issues. | Material impact visible. |
| RBE-FR-012 | 14 | Equipment review | Show equipment used, eligibility at operation time, calibration/qualification/cleaning exceptions. | Equipment evidence. |
| RBE-FR-013 | 14 | Environment/sterile review | Where applicable show EM excursions, interventions, sterilization/filter/hold-time blockers. | Sterile DDCP review. |
| RBE-FR-014 | 14 | Genealogy completeness | Confirm required constituent/material/component/serial relationships exist and no unresolved gaps. | Release trace complete. |
| RBE-FR-015 | 14 | Packaging/label review | Show line clearance, label version, issuance/reconciliation, UDI, packaging inspection and discrepancies. | Packaging release evidence. |
| RBE-FR-016 | 14 | Yield/reconciliation | Show theoretical/actual yield, phase calculations and material/label/packaging reconciliation with variance status. | Numerical blockers visible. |
| RBE-FR-017 | 14 | Reviewer comment | QA can add structured comment/question linked to exact record/exception/evidence; comment is audited. | Review dialogue attributable. |
| RBE-FR-018 | 14 | Return for controlled action | QA can request correction/investigation/additional evidence through defined action, not edit production data directly. | Separation maintained. |
| RBE-FR-019 | 14 | Review checklist | Product/profile-specific checklist is versioned and snapshot-bound to review package. | Review expectations stable. |
| RBE-FR-020 | 14 | Review completion | Reviewer cannot complete until required checklist items and assigned exceptions are dispositioned or explicitly accepted according to policy. | No incomplete closure. |
| RBE-FR-021 | 14 | Multi-reviewer | Support specialist review sections (QC, Device Quality, Drug Quality, Sterile, Packaging) and final QA consolidation where required. | DDCP cross-functional review. |
| RBE-FR-022 | 14 | Review SoD | Review/release roles and prior execution participation evaluated through Document 07. | Independent review. |
| RBE-FR-023 | 14 | Review signature | Review completion uses regulated e-signature when in Part 11 scope; binds review package version/hash. | Exact review signed. |
| RBE-FR-024 | 14 | Review re-open | New evidence/correction after review completion invalidates/reopens affected review and requires re-evaluation/signature. | No stale review. |
| RBE-FR-025 | 14 | Risk-based routing | Rules may route high-risk exceptions to additional reviewers but cannot reduce mandatory customer/regulatory review requirements. | Escalation safe. |
| RBE-FR-026 | 14 | Search/trending | QA dashboard can filter batches by exception class, review age, product/site and blockers. | Operational quality management. |
| RBE-FR-027 | 14 | Export | Review package included in final batch export with checklist, reviewer comments, signatures and exception disposition. | Inspection-ready. |
| RBE-FR-028 | 14 | Performance | Exception index generated asynchronously but review cannot falsely show 'complete' until index/completeness status is current. | No stale green status. |
| RBE-FR-029 | 14 | Integrity health | Audit/evidence integrity failures appear as review blockers. | Tamper signal impacts release. |
| RBE-FR-030 | 14 | Review record retention | Review comments/checklists/signatures retained with batch record. | Long-term evidence. |
| REL-FR-001 | 15 | Release scope | Define release/disposition object for exact product/batch/device lot/serial/combination scope. | Decision target unambiguous. |
| REL-FR-002 | 15 | Separate DDCP final release | Drug/device constituent acceptance/release are prerequisites but never automatically equal final combination-product release. | Final DDCP authority separate. |
| REL-FR-003 | 15 | Eligibility evaluation | Evaluate released rule set against manufacturing completeness, QA review, QC, QMS, materials, equipment, environment, packaging, genealogy, yield/reconciliation and signatures. | No manual checklist-only release. |
| REL-FR-004 | 15 | Blocker model | Return machine-readable blockers with severity, source record and resolution action. | User knows exact reason. |
| REL-FR-005 | 15 | Warning model | Warnings may require acknowledgement/comment but cannot be used to downgrade mandatory blocker without controlled rule/change. | No ad hoc bypass. |
| REL-FR-006 | 15 | QA authority | Only authorized current QA Release signer(s) may execute final release/disposition. | Authority controlled. |
| REL-FR-007 | 15 | Step-up signature | Final release/reject/disposition uses Document 04 signature bound to exact release package/version/hash. | Exact decision signed. |
| REL-FR-008 | 15 | Re-evaluation before commit | Immediately before release commit, recheck batch version, eligibility rules, open blockers and signature validity. | No stale green status. |
| REL-FR-009 | 15 | Release snapshot | Commit immutable release package containing exact decision inputs, rule versions, review package, signatures, batch/record hash and genealogy completeness status. | Historical release reproducible. |
| REL-FR-010 | 15 | Release states | Draft Evaluation, Eligible, Blocked, Pending Signature, Released, Rejected, Hold, Rework, Reprocess, Destruction, Return/Other configured disposition. | Explicit disposition. |
| REL-FR-011 | 15 | Hold disposition | Quality can place release hold with reason and signature; release eligibility may continue updating but product cannot distribute. | Hold enforced. |
| REL-FR-012 | 15 | Reject | Reject decision records reason, affected scope, inventory status and downstream disposition requirement. | Rejected product controlled. |
| REL-FR-013 | 15 | Rework/reprocess | Disposition links to approved route; original release scope remains unreleased until new execution/review complete. | No shortcut. |
| REL-FR-014 | 15 | Destruction | Disposition can require destruction workflow/evidence/witness before closure. | Material/product accounted. |
| REL-FR-015 | 15 | Partial release | Only supported when product/profile explicitly allows defined sub-lot/serial scope with independent genealogy/QC/reconciliation; default disabled. | No accidental partial release. |
| REL-FR-016 | 15 | Serial release | Device units may inherit lot release only when profile/rules permit and all unit exceptions are resolved. | High-volume support. |
| REL-FR-017 | 15 | Expiry/retest/status | Evaluate expiration, stability/release test and relevant constituent status rules. | Expired/ineligible product cannot release. |
| REL-FR-018 | 15 | Open QMS events | Evaluate deviations/OOS/OOT/NCR/CAPA dependencies according to released profile; unresolved critical event blocks. | Quality integrated. |
| REL-FR-019 | 15 | Material status | All consumed critical material lots must have acceptable use status or approved deviation captured. | Traceable. |
| REL-FR-020 | 15 | Equipment status at use | Eligibility considers equipment status at operation time and unresolved equipment-impact events. | Historical correctness. |
| REL-FR-021 | 15 | Sterile/environment | Applicable sterile/environmental release evidence and excursion dispositions required. | Aseptic product support. |
| REL-FR-022 | 15 | Packaging/label | Packaging completion, label correctness and reconciliation required where applicable. | Final product correctly labeled. |
| REL-FR-023 | 15 | Genealogy | Required material/constituent/serial/package genealogy completeness required. | Recall-ready. |
| REL-FR-024 | 15 | Yield/reconciliation | Configured yield/material/label reconciliation within limits or resolved investigation required. | Numerical closure. |
| REL-FR-025 | 15 | Review package | QA review must be current/not invalidated and signed when required. | Review not stale. |
| REL-FR-026 | 15 | Release correction | Release decision itself cannot be edited; if later found erroneous, create controlled post-release quality/field-action path, not overwrite history. | Release history immutable. |
| REL-FR-027 | 15 | Distribution integration | After release, emit event to ERP/WMS; integration failure does not undo release but prevents/flags downstream availability according to interface policy. | System boundaries clear. |
| REL-FR-028 | 15 | Release certificate/export | Generate release summary/certificate if configured, with signer, time, product/batch, decision and source package hash. | Customer evidence. |
| REL-FR-029 | 15 | Release audit | Audit eligibility evaluation, blockers, acknowledgements, signature and final decision. | Inspection-ready. |
| REL-FR-030 | 15 | Bulk release | Batching multiple independent release scopes into one UI action may be allowed, but each scope gets independent eligibility/signature binding/decision record. | No one signature ambiguously covers unknown scope. |
| REL-FR-031 | 15 | Revoke availability | Post-release hold/recall is a new controlled status/action; released historical decision remains intact. | No history rewrite. |
| REL-FR-032 | 15 | Release SLA metrics | Track review/release cycle time and blocker aging without influencing regulatory decision. | Operational analytics. |
| PKG-FR-001 | 16 | Packaging configuration | Use released packaging configuration tied to product/version and packaging level. | Correct materials/process. |
| PKG-FR-002 | 16 | Packaging material eligibility | Verify packaging components/material lots are released, correct, unexpired and approved for product. | Wrong packaging blocked. |
| PKG-FR-003 | 16 | Label master/version | Reference exact released label/artwork/template version and approved variable-data schema. | No latest-label ambiguity. |
| PKG-FR-004 | 16 | Label issuance | Issue controlled quantity/range/job with product/batch/lot/serial scope, label version, operator/system source and time. | Strict issuance trace. |
| PKG-FR-005 | 16 | Label examination | Before use/release, verify identity/conformity and required fields; device profiles include applicable UDI, expiration/storage/handling instructions. | Pre-use correctness. |
| PKG-FR-006 | 16 | Print integration | Integrate label printer/label management system through adapter; each print job has immutable ID, template version, variable data hash and printer source. | Printed label reproducible. |
| PKG-FR-007 | 16 | Reprint | Reprint requires reason, authorization and controlled reprint counter/status; original/reprint history retained. | No uncontrolled duplicate labels. |
| PKG-FR-008 | 16 | Serialization | Where required allocate/consume serials/UDI PI values and prevent duplicate assignment. | Unique units. |
| PKG-FR-009 | 16 | Line clearance | Require packaging line clearance before start/changeover and capture prior-product/material/label clearance checklist. | Mix-up prevention. |
| PKG-FR-010 | 16 | Packaging execution | Record packaging line/equipment, start/end, operators, materials, quantities, inspections and interruptions. | Complete packaging history. |
| PKG-FR-011 | 16 | Label application verification | Verify applied label matches product/batch/serial/package; barcode/vision scan preferred where available. | Wrong label detected. |
| PKG-FR-012 | 16 | Packaging inspection | Capture visual/automated inspection results and defect/reject code. | Acceptance evidence. |
| PKG-FR-013 | 16 | Label reconciliation | Reconcile issued, used, returned, destroyed, rejected and unused label quantities according to released policy. | Discrepancies surfaced. |
| PKG-FR-014 | 16 | Reconciliation waiver/profile | Only apply allowed reconciliation exceptions/waivers when specifically configured under applicable rule/profile and alternate examination evidence exists. | No broad waiver. |
| PKG-FR-015 | 16 | Excess controlled label destruction | Record destruction of excess lot/control-number labels with quantity, reason and witness/authority where required. | No uncontrolled surplus. |
| PKG-FR-016 | 16 | Returned label control | Returned labels maintain identity/status/location to prevent mix-ups. | Reusable stock controlled. |
| PKG-FR-017 | 16 | Packaging reconciliation | Reconcile packaging component quantities and finished pack counts, rejects, samples and destruction. | Material balance. |
| PKG-FR-018 | 16 | Package hierarchy | Create unit→carton→shipper/pallet hierarchy and genealogy where applicable. | Distribution trace. |
| PKG-FR-019 | 16 | Aggregation correction | Wrong aggregation relationship corrected through controlled event preserving original. | Serialization history. |
| PKG-FR-020 | 16 | Tamper-evident profile | Where applicable support tamper-evident packaging checks/evidence through product profile. | Profile-specific compliance. |
| PKG-FR-021 | 16 | Expiration | Print/capture expiration from released rule/product data; operator cannot free-type controlled expiry unless allowed workflow. | Dating controlled. |
| PKG-FR-022 | 16 | UDI | Device/DDCP label execution supports exact DI/PI construction/source and records UDI by device/lot as applicable. | Current device requirement support. |
| PKG-FR-023 | 16 | Artwork/spec evidence | Packaging record references approved artwork/specification/version and sample/specimen or image/evidence where configured. | Historical label evidence. |
| PKG-FR-024 | 16 | Packaging hold | Line or batch packaging can be held for label/material/equipment/quality issue. | Stop mix-up. |
| PKG-FR-025 | 16 | Changeover | Controlled end/start between product/batch/label versions includes clearance and reconciliation closure. | Safe transition. |
| PKG-FR-026 | 16 | Rejected packages | Track rejected units/packages, defect reason, rework/scrap disposition and serial status. | No ghost product. |
| PKG-FR-027 | 16 | Samples | Account for retained/QC/inspection samples in packaging reconciliation where applicable. | Quantity balance. |
| PKG-FR-028 | 16 | Final packaging completion | Cannot complete packaging stage until required inspections, line clearance closure and reconciliations are acceptable/resolved. | Release blocker. |
| PKG-FR-029 | 16 | ERP/WMS posting | Post packaged finished quantity/status/reference after GxP commit using adapter and idempotency. | Financial/warehouse sync. |
| PKG-FR-030 | 16 | Audit/export | Packaging/label history appears in batch/device record export, including issuance, reprints, reconciliation and inspections. | Inspection-ready. |
| PKG-FR-031 | 16 | Electronic record correction | Incorrect captured label/packaging data uses controlled correction, never direct edit. | Data integrity. |
| PKG-FR-032 | 16 | Printer/device identity | Printer, scanner, vision system and applicator sources are registered/attributable where automated evidence is used. | Source trusted. |
| YLD-FR-001 | 17 | Theoretical yield definition | Recipe/product defines theoretical yield or measure at appropriate manufacturing phases using released calculation/rule versions. | Expected output controlled. |
| YLD-FR-002 | 17 | Actual yield source | Actual yield derives from authoritative measured/recorded output quantities and source/equipment/manual evidence. | No untraceable number. |
| YLD-FR-003 | 17 | Yield percentage | Calculate percentage of theoretical yield using validated decimal formula and explicit rounding. | Reproducible result. |
| YLD-FR-004 | 17 | Independent verification | Where required, calculated yield is independently verified or verified per automated-equipment rule/profile. | Support applicable 211.103 workflow. |
| YLD-FR-005 | 17 | Phase yield | Support multiple phase/stage calculations, not only final yield. | Process loss visible. |
| YLD-FR-006 | 17 | Yield limits | Released recipe defines min/max percentage or other acceptance rule and investigation trigger. | Out-of-limit automatic. |
| YLD-FR-007 | 17 | Automated calculation | Automated calculation records input references, rule version, engine version and result; verifier sees inputs/result. | Transparent automation. |
| YLD-FR-008 | 17 | Manual calculation fallback | If calculation manually entered/externally calculated, require source, reason/policy and verification; default prefer engine calculation. | Fallback controlled. |
| YLD-FR-009 | 17 | Material mass balance | Reconcile received/issued/dispensed/consumed/returned/rejected/destroyed/loss quantities for defined scope. | Material accountability. |
| YLD-FR-010 | 17 | Dispensing reconciliation | For each material requirement reconcile dispensed vs consumed/returned/approved loss. | Per-material closure. |
| YLD-FR-011 | 17 | Packaging material balance | Reconcile packaging components issued/used/rejected/returned/destroyed/samples. | Packaging accountability. |
| YLD-FR-012 | 17 | Label reconciliation | Consume Document 16 label counts and applicable waiver/profile rule. | Unified release blocker. |
| YLD-FR-013 | 17 | Device component reconciliation | For serialized/critical components reconcile issued/assembled/rejected/scrapped/returned where configured. | Component accountability. |
| YLD-FR-014 | 17 | Unit count reconciliation | Reconcile produced/accepted/rejected/reworked/sampled/scrapped packaged unit counts. | Finished quantity consistent. |
| YLD-FR-015 | 17 | Potency correction | Calculate required active material amount from released potency/assay result and formula/version. | Drug dispensing support. |
| YLD-FR-016 | 17 | Overage/excess | Recipe may define justified component excess/overage as released parameter; system distinguishes planned excess from variance. | No hidden overage. |
| YLD-FR-017 | 17 | Unit conversion | All calculations use controlled UOM service and explicit dimensional conversion. | No mixed-unit error. |
| YLD-FR-018 | 17 | Precision/rounding | Each calculation has explicit decimal precision, rounding mode and stage. | No developer default. |
| YLD-FR-019 | 17 | Tolerance | Reconciliation defines absolute/percentage tolerance and inclusive/exclusive semantics. | Boundary deterministic. |
| YLD-FR-020 | 17 | Variance | Outside-tolerance result creates blocker and linked deviation/investigation according to profile. | No silent acceptance. |
| YLD-FR-021 | 17 | Approved loss | Document controlled reasons/categories for process loss, sample, spill, reject, destruction; approval may be required. | Variance explained. |
| YLD-FR-022 | 17 | Correction | Input/result correction preserves original and automatically re-evaluates affected downstream yields/reconciliations/review. | Consistency maintained. |
| YLD-FR-023 | 17 | Snapshot rule version | Batch uses exact calculation/reconciliation rules included in issue snapshot. | Historical reproducibility. |
| YLD-FR-024 | 17 | Rework/reprocess accounting | Original and rework material/output remain linked; no double-counting. | True balance. |
| YLD-FR-025 | 17 | Partial batch/sub-lot | Where supported, calculate and reconcile by defined scope and aggregate to parent. | Partial release support. |
| YLD-FR-026 | 17 | Serial/device scope | Unit count/component usage may aggregate serial-level data without losing exception visibility. | High-volume support. |
| YLD-FR-027 | 17 | External inventory reconciliation | ERP/WMS quantity may be compared after GxP calculation; discrepancy flagged but ERP never overwrites GxP evidence automatically. | Boundary clear. |
| YLD-FR-028 | 17 | Review display | QA sees source quantities, formulas, calculation versions, results, tolerances, variances and investigations. | Reviewable. |
| YLD-FR-029 | 17 | Release blocker | Required unresolved yield/reconciliation failures block release. | Quality gate. |
| YLD-FR-030 | 17 | Export | Final batch record includes yield and reconciliation results plus verification/signature and variance disposition. | 211.188-style evidence support. |
| YLD-FR-031 | 17 | Calculation trace | For every result retain input IDs/versions/values, calculation rule, engine version, time and verifier/signature if required. | Reproducible. |
| YLD-FR-032 | 17 | Performance | Large serial/component reconciliations may run asynchronously but final state is versioned and release waits for current result. | Scale safe. |
