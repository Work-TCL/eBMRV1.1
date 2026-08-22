# WP-02 — Scope & Requirements

**In scope:** Documents 09, 10, 11, 12

## Document 09 — Product, Constituent & Regulatory Profile Master (SPEC-EBMR-000)

- Code location: `services/gxp-api/src/modules/ebmr`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: PRD-FR-001..032 (32)

## Document 10 — Master Recipe / Master Manufacturing Record Specification (SPEC-EBMR-001)

- Code location: `services/gxp-api/src/modules/ebmr`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: RCP-FR-001..036 (36)

## Document 11 — Batch Execution Engine & State Machine Specification (SPEC-EBMR-002)

- Code location: `services/gxp-api/src/modules/ebmr`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: BAT-FR-001..036 (36)

## Document 12 — eDHR / Device Production History Specification (SPEC-EBMR-003)

- Code location: `services/gxp-api/src/modules/ebmr`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: DHR-FR-001..030 (30)

## All requirements

| ID | Doc | Requirement | Behaviour | Acceptance |
|---|---|---|---|---|
| PRD-FR-001 | 09 | Product master | Create controlled product identity with immutable internal ID, business code, marketed/internal names, lifecycle state, product family, dosage/device form, strength/configuration, manufacturing profil | Product can be uniquely referenced across recipes, batches, QC, genealogy and release. |
| PRD-FR-002 | 09 | Product lifecycle | Support Draft, Under Review, Approved/Released, Effective, Suspended, Obsolete, Superseded. Released product versions are immutable. | Obsolete/suspended product cannot start new production unless controlled exception policy  |
| PRD-FR-003 | 09 | Product version | Product changes create a new version with effective dating and Vault release; historical batches remain linked to prior version. | No silent historical drift. |
| PRD-FR-004 | 09 | Constituent model | A DDCP product may contain Drug, Device, Biologic, HCT/P or Other constituent types; V1 actively supports Drug + Device and structurally supports later profiles. | Combination product is not represented as two unrelated masters. |
| PRD-FR-005 | 09 | Constituent role | Record primary/secondary constituent role, manufacturer/site source, business identity, exact version, lot/serial strategy and regulated handoff requirements. | Cross-constituent evidence can be validated. |
| PRD-FR-006 | 09 | Combination-product type | Support Single Entity, Co-Packaged and Cross-Labeled/Other relationship metadata as controlled product attributes; exact regulatory applicability remains customer/regulatory decision. | Workflow can distinguish product relationship type. |
| PRD-FR-007 | 09 | PMOA metadata | Store customer-approved PMOA/lead-center/regulatory-context reference without software deciding PMOA. | Product does not infer regulatory classification. |
| PRD-FR-008 | 09 | Part 4 operating-system profile | Store customer-approved compliance approach/profile reference and applicable supplementary control set. | Release/rules can select applicable profile. |
| PRD-FR-009 | 09 | Manufacturing profile | Assign one or more controlled manufacturing profiles: Injectable DDCP, Inhalation DDCP, Drug-Eluting/Coated Device, Device, Pharma, future extensions. | Recipe authoring can inherit valid process capabilities. |
| PRD-FR-010 | 09 | Sterile/aseptic applicability | Flag whether sterile/aseptic controls apply and reference released sterile-process profile rather than free-text setting. | Sterile-required product cannot use non-sterile recipe path. |
| PRD-FR-011 | 09 | Lot/serial strategy | Configure finished lot, device lot, unit serial, combination-product serial, or hybrid genealogy strategy. | Execution creates required identifiers. |
| PRD-FR-012 | 09 | UDI applicability | Configure UDI requirement, issuing-agency metadata, DI rules, production-identifier sources and packaging-level requirements where applicable. | Device/combination records support UDI capture. |
| PRD-FR-013 | 09 | Drug batch identity strategy | Configure drug batch/lot identification and whether final product shares or differs from drug-constituent batch identity. | Genealogy remains explicit. |
| PRD-FR-014 | 09 | Strength/concentration | Represent drug strength/concentration using structured quantity + UOM and product-specific calculation metadata. | No free-text-only strength. |
| PRD-FR-015 | 09 | Device configuration | Represent device model/configuration/version and compatible drug constituent constraints. | Wrong device configuration cannot be paired. |
| PRD-FR-016 | 09 | Constituent compatibility | Release controlled compatibility versions specifying allowed exact drug/device constituent combinations and critical interface constraints. | Final DDCP issue checks compatibility. |
| PRD-FR-017 | 09 | Packaging configuration | Reference released packaging hierarchy/configuration and label profile by product/version. | Packaging module uses exact approved configuration. |
| PRD-FR-018 | 09 | Shelf-life/expiration profile | Reference released expiration/stability policy; product master does not hard-code computed expiration logic. | Expiration is rule/profile driven. |
| PRD-FR-019 | 09 | Storage conditions | Reference structured storage/environment requirements and acceptable ranges. | Warehouse and batch rules can evaluate conditions. |
| PRD-FR-020 | 09 | Material/BOM relationship | Reference approved material/component structures; material specification versions remain separate controlled objects. | Product version does not duplicate mutable material specs. |
| PRD-FR-021 | 09 | Quality specification links | Reference released finished/in-process/device test specifications and sampling profiles. | QC receives correct requirements. |
| PRD-FR-022 | 09 | Equipment/process class requirements | Reference allowed equipment/process classes and special validation requirements. | Recipe validation checks compatibility. |
| PRD-FR-023 | 09 | Site admission | Product version has approved manufacturing/packaging/release sites and optional contract-manufacturing relationships. | Unauthorized site cannot issue batch. |
| PRD-FR-024 | 09 | Regulatory attribute provenance | Critical regulatory profile fields store source/decision reference, approver and effective version. | Audit can show basis of configuration. |
| PRD-FR-025 | 09 | Product change impact | Changing regulated product attributes triggers impact assessment for recipes, specs, labels, QC, validation, inventory, open batches and genealogy. | Downstream affected objects identified. |
| PRD-FR-026 | 09 | Clone/template creation | Allow draft clone from approved family/template, but cloned product receives new identity and requires full review/release. | No inherited approval. |
| PRD-FR-027 | 09 | Search/filter | Search by code, name, constituent type, manufacturing profile, site, lifecycle, UDI DI, device model, strength. | Operational usability. |
| PRD-FR-028 | 09 | API/integration mapping | Maintain external-system IDs for ERP/LIMS/label systems without using external ID as internal primary key. | ERP mappings do not contaminate domain identity. |
| PRD-FR-029 | 09 | Product suspension | Quality may suspend future issue with reason/signature while preserving active/in-process batch policy separately. | Suspension does not rewrite past batches. |
| PRD-FR-030 | 09 | Inspection export | Produce human-readable product/profile/version report with constituents, applicability, approved sites, labels/spec references and release signatures. | Controlled master can be reviewed externally. |
| PRD-FR-031 | 09 | Configuration completeness | Before product release, validate mandatory attributes based on active manufacturing/regulatory profile. | Incomplete DDCP cannot release. |
| PRD-FR-032 | 09 | Profile admission gate | Unsupported specialist context (e.g. biologic-specific or unsupported implantable/connected-device profile) fails closed unless corresponding profile package is approved. | Configuration cannot enable unsupported scope. |
| RCP-FR-001 | 10 | Recipe family | Create recipe/MMR family under exact product version/profile and manufacturing site scope. | Recipe has clear governing product. |
| RCP-FR-002 | 10 | Recipe version lifecycle | Draft, review, approved/released, effective, superseded, obsolete, suspended. Released version immutable. | Production only uses eligible release. |
| RCP-FR-003 | 10 | Batch-size variants | Support controlled batch-size variants and scaling policy; drug profile may require distinct master records by batch size as applicable. | Scaling is never an uncontrolled multiplier. |
| RCP-FR-004 | 10 | Structured sections | Recipe contains ordered sections/stages with purpose, area, expected duration and dependencies. | No single free-text blob. |
| RCP-FR-005 | 10 | Step definition | Each step has stable step ID, instruction, type, sequence/dependencies, performer role, inputs, outputs, validations and completion criteria. | Executable semantics explicit. |
| RCP-FR-006 | 10 | Step types | Support Instruction, Data Entry, Scan, Weigh, Equipment Check, Calculation, IPC/QC, Signature, Verification, Timer, Hold Point, Material Consume, Assembly, Test, Packaging, Custom Approved Type. | Common engine reusable. |
| RCP-FR-007 | 10 | Dependencies | Directed dependency graph supports sequential, parallel and join behavior without cycles unless an explicitly modelled repeat/rework structure is used. | Graph validates before release. |
| RCP-FR-008 | 10 | Conditional branches | Released rule determines branch based on structured result; operator cannot choose hidden uncontrolled path. | Branch reason auditable. |
| RCP-FR-009 | 10 | Material requirements | Each requirement references material/component specification, target quantity/formula, tolerance, stage and alternative-policy reference. | Wrong material blocked. |
| RCP-FR-010 | 10 | Equipment requirements | Step references equipment class/asset eligibility, qualification/calibration/cleaning status and optional redundancy. | Equipment checks enforceable. |
| RCP-FR-011 | 10 | Personnel requirements | Step references roles, training and qualifications including independent verifier where required. | Execution gating possible. |
| RCP-FR-012 | 10 | Area/environment requirement | Step references permitted site/area/room/line and environmental/sterile profile. | Execution location constrained. |
| RCP-FR-013 | 10 | Parameter definition | Structured parameter includes code, label, type, UOM, source, target/limits, precision, mandatory flag and rule references. | Data capture validated. |
| RCP-FR-014 | 10 | Source type | Parameter source can be Manual, Device/Edge, Calculated, LIMS, ERP, Imported Evidence or System; allowed fallback explicitly configured. | Manual substitution cannot occur silently. |
| RCP-FR-015 | 10 | Manual fallback policy | If automated source unavailable, rule defines whether manual entry is prohibited or allowed with reason, qualification and verification/signature. | Fallback controlled. |
| RCP-FR-016 | 10 | Calculation reference | Recipe references released calculation/rule version from Document 08. | No embedded arbitrary formula. |
| RCP-FR-017 | 10 | IPC/QC point | Step can create required sample/test orders, acceptance criteria and continuation/release hold. | QC integrated. |
| RCP-FR-018 | 10 | Timer/hold time | Step may start, pause or stop controlled timer with max/min duration and exception behavior. | Time limits enforced. |
| RCP-FR-019 | 10 | Electronic-signature requirement | Recipe specifies signature policy by step/action without embedding authentication mechanics. | Document 04 reused. |
| RCP-FR-020 | 10 | Independent verification | Step supports performer/verifier and history-aware SoD. | Independent check enforced. |
| RCP-FR-021 | 10 | Attachment/evidence requirement | Step can require photo, instrument file, document, certificate or machine evidence with type constraints. | Evidence completeness testable. |
| RCP-FR-022 | 10 | Instruction version integrity | Instruction shown at execution comes from exact issued recipe snapshot. | Later edits cannot change open batch. |
| RCP-FR-023 | 10 | Line clearance/cleaning | Recipe may require prerequisite line-clearance/cleaning evidence before stage start. | Packaging/sterile controls integrated. |
| RCP-FR-024 | 10 | Sterile-specific step metadata | For applicable profile, support intervention classification, sterile component status, filter/cycle references, hold times and environmental dependencies. | Aseptic profile extensible. |
| RCP-FR-025 | 10 | Device assembly metadata | Support component lot/serial inputs, assembly relationship, device test result and unit/lot scope. | eDHR reuse. |
| RCP-FR-026 | 10 | Packaging/label step | Reference packaging/label configuration and issuance/reconciliation requirements. | Document 16 integration. |
| RCP-FR-027 | 10 | Expected yield points | Declare manufacturing phases at which yield/reconciliation calculation is required. | Document 17 integration. |
| RCP-FR-028 | 10 | Exception policy | Each step defines what happens on out-of-limit, missing evidence, timeout, failed device read or ineligible resource: block, hold, deviation, retry under rule. | No ad hoc operator decision. |
| RCP-FR-029 | 10 | Rework/reprocess route | Approved alternative route is modelled as separate released route/profile; cannot be improvised during batch execution. | Controlled rework. |
| RCP-FR-030 | 10 | Recipe completeness validator | Before release, validate graph, dependencies, missing specs, rules, signature policies, unsupported step types, unused references and profile-specific requirements. | Invalid recipe cannot release. |
| RCP-FR-031 | 10 | Independent master review | Release policy supports author + independent checker/approver; signatures bind exact canonical recipe version. | 211.186-style master control support. |
| RCP-FR-032 | 10 | Effective date and site | Recipe validity depends on product/site/effective date and released dependencies. | Issue eligibility deterministic. |
| RCP-FR-033 | 10 | Change impact | Changing released recipe creates new version and evaluates open batches, materials, labels, validation and training impact. | Existing batch unaffected unless controlled change path. |
| RCP-FR-034 | 10 | Recipe compare | Provide semantic version comparison: instructions, steps, limits, materials, equipment, rules, signatures, branches. | Reviewer can see critical change. |
| RCP-FR-035 | 10 | Simulation | Non-production simulation validates graph/rules/inputs without creating regulated batch. | Authoring quality improved. |
| RCP-FR-036 | 10 | Template reuse | Reusable step/section templates may be inserted into draft recipe; final recipe stores resolved exact template version/content. | No live mutable template at execution. |
| BAT-FR-001 | 11 | Batch creation | Create batch from effective product + recipe version, site, target quantity and allowed production order/reference. | Batch source fully attributable. |
| BAT-FR-002 | 11 | Unique identity | Assign immutable batch ID plus controlled human batch number. Prevent duplicate/reused business numbers by tenant/site policy. | Unique batch traceability. |
| BAT-FR-003 | 11 | Issue snapshot | At issue, create immutable execution snapshot from exact released dependencies. | Open batch immune to later master changes. |
| BAT-FR-004 | 11 | Batch lifecycle | Authoritative states: Planned, Created/Snapshot Locked, Issued, Ready, In Execution, On Hold, Exception Pending, Production Complete, QA Review, Released/Rejected/Other Disposition, Closed. | State machine explicit. |
| BAT-FR-005 | 11 | Step instance creation | Instantiate executable step instances from snapshot with stable recipe step reference and batch-specific state. | Execution has immutable parent instruction. |
| BAT-FR-006 | 11 | Step readiness | Compute readiness from predecessors, conditions, material/equipment/personnel requirements, holds and quality blockers. | UI cannot force readiness. |
| BAT-FR-007 | 11 | Step claim/start | Authorized operator may claim/start ready step; record operator, area, equipment context and start time. | Who/where/when captured. |
| BAT-FR-008 | 11 | Concurrent execution | Support parallel independent steps with version/concurrency protection and explicit join conditions. | No cross-step overwrite. |
| BAT-FR-009 | 11 | Parameter capture | Capture typed value, UOM, source, source timestamp, receive time, actor/device, quality status and applicable rule result. | Complete evidence. |
| BAT-FR-010 | 11 | Manual entry | Manual result records actor, reason/source and verification policy; replacing unavailable automated input requires allowed fallback path. | Manual substitution visible. |
| BAT-FR-011 | 11 | Device/Edge result | Accept registered device data with source identity, sequence/idempotency, mapping version and data-quality status. | Machine evidence attributable. |
| BAT-FR-012 | 11 | Material consume | Step invokes Material Service eligibility/reservation/dispensing/consumption command; genealogy relationship committed. | Batch knows exact material lots/containers. |
| BAT-FR-013 | 11 | Equipment use | Verify equipment eligibility at start and relevant completion; capture actual equipment IDs. | Equipment history exact. |
| BAT-FR-014 | 11 | Qualification gate | Verify performer/verifier training/qualification at action time. | Unqualified action blocked. |
| BAT-FR-015 | 11 | Step validation | Before completion validate required parameters, evidence, calculations, QC requirements, materials and signatures. | Incomplete step cannot complete. |
| BAT-FR-016 | 11 | Step signature | When required, completion/verification consumes Document 04 signature bound to exact step/result version. | Signature exact. |
| BAT-FR-017 | 11 | Independent verification | Support second-person verification with SoD and exact values/evidence being verified. | Checker knows what was checked. |
| BAT-FR-018 | 11 | Timer | Start/stop/measure controlled durations; time-limit breach generates configured exception/hold. | Hold time enforced. |
| BAT-FR-019 | 11 | Pause/resume | Pause reason/status retained; resume revalidates relevant resources if policy requires. | Long interruptions safe. |
| BAT-FR-020 | 11 | Batch hold | Authorized command holds whole batch or scoped stage/step; reason/signature and source quality event captured. | No execution past hold. |
| BAT-FR-021 | 11 | Exception generation | Out-of-limit, missing/invalid evidence, timeout, material/equipment/qualification failure or manual override generates linked exception according to rule. | Deviation not optional. |
| BAT-FR-022 | 11 | Conditional branch | Evaluate released branch rule and activate exact downstream path; unselected path marked Not Applicable with reason/reference. | Record explains path. |
| BAT-FR-023 | 11 | Step correction | Completed step data correction uses controlled correction workflow preserving original, reason, impact and signatures. | No edit-in-place. |
| BAT-FR-024 | 11 | Rework/reprocess | Only released rework/reprocess route can be instantiated after authorized disposition; history links original and new route. | No improvised rework. |
| BAT-FR-025 | 11 | Shift handover | Support controlled operator handover without changing prior attribution; active step may require pause/checklist/signature. | Continuity maintained. |
| BAT-FR-026 | 11 | Production completion | Batch can become Production Complete only when all required applicable steps, yields/reconciliations and production blockers are resolved. | Completeness deterministic. |
| BAT-FR-027 | 11 | QA review handoff | Create review snapshot/index and lock production inputs except controlled correction/action path. | QA reviews stable evidence. |
| BAT-FR-028 | 11 | Temporal orchestration | Use Temporal for waits/timers/retries/parallel orchestration; authoritative state remains PostgreSQL. | Workflow engine not record truth. |
| BAT-FR-029 | 11 | Restart/recovery | Worker/application restart resumes from authoritative batch/Temporal state without duplicate regulated actions. | Resilient long-running batch. |
| BAT-FR-030 | 11 | Integration outage | ERP/LIMS/Edge outage follows profile rules: buffer/pending/hold; never fabricate completion/pass. | Fail safe. |
| BAT-FR-031 | 11 | Batch abort/cancel | Controlled abort/void retains all data, reason, status, material/equipment impact and disposition requirement. | No deletion. |
| BAT-FR-032 | 11 | Unit/serial scope | Steps may execute at batch/lot/unit/serial/subassembly scope depending on profile. | Device/DDCP reuse. |
| BAT-FR-033 | 11 | Late data | Late device/LIMS data is accepted only through defined rule with source timestamp and batch-state impact; cannot silently alter released decision. | Late evidence controlled. |
| BAT-FR-034 | 11 | Execution comments | Structured comments/notes may be added with author/time; corrections to comments preserve history if regulated. | Communication auditable. |
| BAT-FR-035 | 11 | Production dashboard | Show active batches, current step, holds, exceptions, timers and resource blockers without exposing unauthorized data. | Operational visibility. |
| BAT-FR-036 | 11 | Batch export readiness | At any time, system can produce current structured record; final inspection export after release comes from authoritative records. | No hidden spreadsheet reconstruction. |
| DHR-FR-001 | 12 | Device production record | Create complete lot/unit/serial production history derived from released product/recipe snapshot. | Device history reproducible. |
| DHR-FR-002 | 12 | Scope level | Support lot-level, serial-level, subassembly-level and inherited batch-level evidence. | High-volume execution configurable. |
| DHR-FR-003 | 12 | Serial generation/import | Generate or accept controlled serials with uniqueness, source and reservation rules. | No duplicate device identity. |
| DHR-FR-004 | 12 | UDI record | Store applicable DI/PI/UDI components, packaging level and source; link to unit/lot/batch history. | Current QMSR/UDI record support. |
| DHR-FR-005 | 12 | Component genealogy | Record exact device component lots/serials/subassemblies assembled into final device. | Backward/forward traceability. |
| DHR-FR-006 | 12 | Drug constituent linkage | For DDCP, link exact drug batch/lot/container/fill group to device unit/lot/combination product. | Integrated history. |
| DHR-FR-007 | 12 | Assembly step | Capture assembly station/equipment, operator/device source, time, parameters and component relationships. | Assembly evidence attributable. |
| DHR-FR-008 | 12 | Test result | Capture functional/electrical/mechanical/dose-delivery/visual or other structured test result with test specification/version. | Acceptance evidence exact. |
| DHR-FR-009 | 12 | Automated tester | Accept instrument result through Edge with source identity, mapping version, raw evidence reference and pass/fail rule. | Machine result attributable. |
| DHR-FR-010 | 12 | Manual inspection | Capture inspector, method, criteria, result, defect code and optional image/evidence. | Manual acceptance controlled. |
| DHR-FR-011 | 12 | Nonconformance | Failed component/unit/test creates linked NCR/exception and controls disposition. | Failure not overwritten. |
| DHR-FR-012 | 12 | Rework | Rework uses approved route and maintains original + reworked history, reason and approvals. | Rework traceable. |
| DHR-FR-013 | 12 | Scrap | Unit/component scrap records quantity/identity, reason, authority and genealogy impact. | Scrapped unit cannot release. |
| DHR-FR-014 | 12 | Acceptance status | Unit/lot status progresses through controlled states: In Process, Hold, Rework, Accepted, Rejected/Scrapped, Released. | Status rule driven. |
| DHR-FR-015 | 12 | Label/packaging link | Record exact label/UDI/packaging configuration used for device/lot/unit. | Packaging evidence linked. |
| DHR-FR-016 | 12 | Sterilization link | Where applicable link unit/lot to sterilization load/cycle and release status. | Sterilization eligibility visible. |
| DHR-FR-017 | 12 | Environmental/area link | Where required retain relevant production area/environmental evidence references. | Critical conditions linked. |
| DHR-FR-018 | 12 | Process validation reference | Step/equipment/process may reference applicable validated process version/status. | Production history supports validation linkage. |
| DHR-FR-019 | 12 | Calibration/test-equipment eligibility | Tester/equipment must be eligible when used; actual equipment ID stored. | Invalid tester blocks. |
| DHR-FR-020 | 12 | Production specification snapshot | Device history binds exact released specification/instructions/configuration. | No current-master drift. |
| DHR-FR-021 | 12 | Device record completeness | Before acceptance/release, evaluate required steps, components, tests, labels, signatures and unresolved NCRs. | Incomplete unit cannot release. |
| DHR-FR-022 | 12 | Bulk inheritance | Evidence common to many units may be inherited from batch/lot with immutable reference to avoid duplication. | Scale without semantic loss. |
| DHR-FR-023 | 12 | Override | Any unit-specific override/manual replacement requires released policy, reason, authorization and audit. | No hidden exception. |
| DHR-FR-024 | 12 | Unit split/merge | Support controlled subassembly transformation relationships; final unit genealogy remains acyclic/traceable. | Assembly graph consistent. |
| DHR-FR-025 | 12 | Repair during manufacturing | Distinguish manufacturing rework/repair from postmarket service; apply appropriate controlled route. | Semantics clear. |
| DHR-FR-026 | 12 | Device release package | Generate unit/lot history package with identifiers, components, process, tests, signatures, exceptions, labels and genealogy. | Inspection/customer evidence ready. |
| DHR-FR-027 | 12 | Search | Lookup by serial, UDI, lot, batch, component lot, drug batch, tester, defect code. | Fast investigation. |
| DHR-FR-028 | 12 | High-volume serial execution | Support bulk creation/result ingestion with controlled grouping while preserving unit exceptions. | Scales to many serials. |
| DHR-FR-029 | 12 | Record correction | Corrections use Vault/audit model and never rewrite original device history. | History preserved. |
| DHR-FR-030 | 12 | QMSR terminology | Product may expose customer-facing alias 'eDHR', but compliance mapping is maintained against current QMSR/ISO 13485 record/production controls rather than relying on obsolete clause numbering. | Current regulatory framing. |
