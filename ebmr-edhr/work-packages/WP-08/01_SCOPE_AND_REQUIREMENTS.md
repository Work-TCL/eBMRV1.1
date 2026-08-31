# WP-08 — Scope & Requirements

**In scope:** Documents 54, 55, 56, 57

## Document 54 — Prefilled Syringe & Injectable DDCP Manufacturing Profile (SPEC-DDCP-001)

- Code location: `services/gxp-api/src/modules/ddcp`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: PFS-FR-001..030 (30)

## Document 55 — Autoinjector, Pen Injector & Cartridge-Based DDCP Manufacturing Profile (SPEC-DDCP-002)

- Code location: `services/gxp-api/src/modules/ddcp`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: INJ-FR-001..030 (30)

## Document 56 — Inhalation DDCP Manufacturing Profile — MDI / DPI (SPEC-DDCP-003)

- Code location: `services/gxp-api/src/modules/ddcp`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: INH-FR-001..030 (30)

## Document 57 — Drug-Eluting / Drug-Coated Device DDCP Manufacturing Profile (SPEC-DDCP-004)

- Code location: `services/gxp-api/src/modules/ddcp`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: COAT-FR-001..030 (30)

## All requirements

| ID | Doc | Requirement | Behaviour | Acceptance |
|---|---|---|---|---|
| PFS-FR-001 | 54 | Profile master | Define injectable DDCP subtype, dosage form, presentation, fill volume, strength, device constituent and container-closure architecture. | Concrete product identity. |
| PFS-FR-002 | 54 | Constituent definition | Model drug/biologic constituent, syringe/barrel, stopper/plunger, needle/needle shield, tip cap, safety device and packaging as versioned constituents. | Full genealogy. |
| PFS-FR-003 | 54 | Bulk drug handoff | Receive released bulk drug/biologic batch reference with assay/potency, concentration, sterility/bioburden status and expiry/hold constraints. | Constituent handoff. |
| PFS-FR-004 | 54 | Primary components | Require released lots for barrel/syringe, stopper/plunger, needle/closure and other product-contact components. | No unapproved component. |
| PFS-FR-005 | 54 | Component preparation | Track washing/depyrogenation/sterilization/ready-to-use status according to configured component route. | Sterile readiness. |
| PFS-FR-006 | 54 | Line readiness | Filling line, cleanroom, cleaning, SIP/sterilization, environmental state, personnel and filter status all verified before batch stage start. | Aseptic gate. |
| PFS-FR-007 | 54 | Bulk hold time | Track bulk compounding-to-filtration/filling hold time and block when released limits exceeded. | Validated timing. |
| PFS-FR-008 | 54 | Sterile filtration | If process uses sterile filtration, bind filter lot/serial, pre/post integrity status, filtration parameters and evidence. | Filtration assurance. |
| PFS-FR-009 | 54 | Filling setup | Record filler, product-contact path, fill program/version, needle/nozzle setup, target fill and line configuration. | Setup evidence. |
| PFS-FR-010 | 54 | Fill execution | Capture batch/cycle group, fill start/end, machine counts, actual/IPC weights or volumes, alarms/interventions and rejects. | Complete filling record. |
| PFS-FR-011 | 54 | Fill-weight IPC | Perform configurable in-process fill weight/volume sampling with method, sample frequency and acceptance rule. | Dose quantity control. |
| PFS-FR-012 | 54 | Stoppering/plunging | Capture plunger/stopper insertion/position and relevant process settings/results. | Closure assembly. |
| PFS-FR-013 | 54 | Needle/closure assembly | Track needle installation/shield/tip cap/closure configuration where applicable. | Device constituent. |
| PFS-FR-014 | 54 | Container closure integrity | Link required CCI/leak/seal tests by lot/sample plan/method and release state. | System integrity. |
| PFS-FR-015 | 54 | Visual inspection | 100% or configured inspection records machine/manual inspection version, defect codes, rejects and sampling verification. | Finished presentation quality. |
| PFS-FR-016 | 54 | Silicone/tungsten/particulate profile | Support product-specific material/process attributes or QC references when defined in the product's released control strategy. | Product-specific extensibility. |
| PFS-FR-017 | 54 | Functional syringe tests | Support break-loose/glide force, needle shield/removal force, dose delivery, leakage or other device output tests when included in released specification. | Device performance. |
| PFS-FR-018 | 54 | Safety feature assembly | If needle-safety/guard device exists, track subassembly lot, assembly process and functional test. | Safety constituent. |
| PFS-FR-019 | 54 | Serialization/UDI hooks | Support device/combination-product identifier/UDI configuration where applicable; actual applicability is regulatory-profile controlled. | Future compliance. |
| PFS-FR-020 | 54 | Label/packaging | Link label/artwork version, carton/IFU, lot/expiry and packaging reconciliation. | Finished unit trace. |
| PFS-FR-021 | 54 | Unit/lot genealogy | Drug bulk → component lots → filled syringe lot/unit/sample → packaged lot/device ID relationships preserved. | End-to-end trace. |
| PFS-FR-022 | 54 | Yield reconciliation | Reconcile bulk issued, units filled, rejects, samples, line loss and finished packed quantity. | Mass/unit balance. |
| PFS-FR-023 | 54 | Constituent release | Drug and device-constituent evidence may have separate release checkpoints; final DDCP release remains independent. | Part 4 profile. |
| PFS-FR-024 | 54 | Final release blockers | Open deviations/OOS, failed filter integrity, EM excursion, CCI/functional failure, unresolved reconciliation or missing constituent evidence block release per profile. | No incomplete release. |
| PFS-FR-025 | 54 | Batch review package | Review shows critical aseptic timeline, filtration, fill IPC, interventions, defects, device tests, genealogy and deviations. | Review-by-exception. |
| PFS-FR-026 | 54 | Stability/retain refs | Create/reference stability/retain sample plans and finished lot samples where configured. | Lifecycle support. |
| PFS-FR-027 | 54 | Rework restriction | Filled primary container rework/reprocessing routes are profile-specific and default disallowed unless released procedure explicitly permits. | Safe default. |
| PFS-FR-028 | 54 | Biologic subtype | Biologic constituent can reuse profile, but biologic-specific requirements remain separately enabled/baselined; no implicit equivalency. | Future profile. |
| PFS-FR-029 | 54 | Change sensitivity | Changes to syringe/barrel/stopper/needle/silicone/closure/fill program/filter/control strategy link Change Control and risk/validation impact. | Lifecycle. |
| PFS-FR-030 | 54 | Inspection export | Produce one reproducible PFS/DDCP batch package including drug + device constituent + combined-product evidence. | Inspection-ready. |
| INJ-FR-001 | 55 | Injector family profile | Support autoinjector, pen injector, reusable pen + cartridge, single-use injector and configured related injector architectures. | Reusable family model. |
| INJ-FR-002 | 55 | Drug container relation | Model PFS/cartridge/vial/reservoir as drug-container subassembly and separate injector device constituents. | Exact architecture. |
| INJ-FR-003 | 55 | Device BOM | Track housing, spring/drive, needle system, activation components, dose mechanism, cap, shield, electronics if applicable and packaging. | Device genealogy. |
| INJ-FR-004 | 55 | Subassembly handoff | Released drug-container subassembly enters injector assembly with exact lot/unit range and status. | Constituent handoff. |
| INJ-FR-005 | 55 | Device component release | Only released device component lots/subassemblies can be assembled. | QMS gate. |
| INJ-FR-006 | 55 | Assembly line readiness | Equipment program, tooling, calibration, cleaning/clearance, operator qualification and material verification before run. | Manufacturing gate. |
| INJ-FR-007 | 55 | Assembly recipe | Versioned assembly sequence includes component scans, orientation/presence checks, torque/force/position parameters and verification. | Deterministic assembly. |
| INJ-FR-008 | 55 | Unit serialization | Support unit-level internal serial/UDI/device identifier relationship when profile requires. | Device traceability. |
| INJ-FR-009 | 55 | Drug-container insertion | Track exact PFS/cartridge lot/unit into injector unit/lot; prevent duplicate/cross-use. | Genealogy. |
| INJ-FR-010 | 55 | Needle activation system | Capture assembly/test of needle insertion/retraction/shield function where applicable. | Safety/performance. |
| INJ-FR-011 | 55 | Dose setting mechanism | For pens, capture dose mechanism version/calibration/test route and configured dosing range. | Pen performance. |
| INJ-FR-012 | 55 | Delivery performance outputs | Profile defines essential delivery outputs such as delivered volume/dose, delivery time, activation force, needle depth or other product-specific outputs. | Performance control. |
| INJ-FR-013 | 55 | Function test plan | Sampling or 100% test plan, fixture/program version and acceptance criteria. | Device test evidence. |
| INJ-FR-014 | 55 | Force/torque tests | Support activation/cap removal/needle shield/drive/torque forces and dimensional/functional results. | Mechanical outputs. |
| INJ-FR-015 | 55 | Dose accuracy | Link dose-delivery/gravimetric/volumetric tests and calculations. | Drug delivery. |
| INJ-FR-016 | 55 | Incomplete dose detection | Test/result taxonomy includes under-delivery, partial delivery, premature stop and other profile defects. | Failure modes. |
| INJ-FR-017 | 55 | Audible/visual indicators | Test completion/window/click/indicator functions where included. | User feedback. |
| INJ-FR-018 | 55 | Reusable device pairing | For reusable injector + cartridge, model compatibility/approved pairing and cartridge lot genealogy without assuming permanent single unit relationship. | Cross-labeled architecture. |
| INJ-FR-019 | 55 | Software/electronics | If connected/electronic injector exists, firmware/config/software evidence hooks are available but require separately approved profile. | Future-ready. |
| INJ-FR-020 | 55 | Human factors linkage | Profile can reference design/risk/human-factors critical tasks but manufacturing eBMR does not itself determine usability acceptability. | Lifecycle link. |
| INJ-FR-021 | 55 | Device rejects | Unit reject reason, disassembly/scrap/rework authorization and constituent impact preserved. | Nonconformance. |
| INJ-FR-022 | 55 | Rework | Device rework only through released route; drug-container constituent cannot be casually reused unless procedure explicitly permits and quality status reevaluated. | Controlled. |
| INJ-FR-023 | 55 | Packaging | Device + drug constituent + accessories/IFU/labels/cap/tray/carton reconciliation. | Finished configuration. |
| INJ-FR-024 | 55 | Final device/combination test | Support finished-unit or lot-level tests after assembly/packaging. | Final evidence. |
| INJ-FR-025 | 55 | Genealogy | Component lots + drug-container lot/unit → injector serial/lot → packaged saleable unit. | End-to-end. |
| INJ-FR-026 | 55 | Constituent release | Separate container/drug/device checkpoints feed final combined release. | DDCP. |
| INJ-FR-027 | 55 | Release blockers | Failed dose/function test, unresolved device NCR, wrong component pairing, genealogy gap or incomplete container/drug evidence block final release. | No bypass. |
| INJ-FR-028 | 55 | Change impact | Drive system, spring, needle, cartridge/PFS, lubricant, assembly program, test fixture/program and labeling changes trigger controlled assessment. | Lifecycle. |
| INJ-FR-029 | 55 | Product family inheritance | Common injector profile can inherit product-family functions while exact test outputs/limits are product-version controlled. | Configurability. |
| INJ-FR-030 | 55 | Evidence export | Unit/lot-level combined package supports investigation of one complaint serial back to exact drug and device constituents. | Postmarket readiness. |
| INH-FR-001 | 56 | Inhalation profile | Support MDI, DPI and configured inhalation-device presentations through subtype-specific profile. | Family abstraction. |
| INH-FR-002 | 56 | Drug formulation constituent | Model formulation/blend/suspension/solution constituent with released batch/spec/hold time. | Drug input. |
| INH-FR-003 | 56 | Device/container constituents | MDI valve/canister/actuator or DPI device/capsule/blister/reservoir components tracked as device/container constituents. | Device trace. |
| INH-FR-004 | 56 | Propellant/excipient components | For MDI, propellant/excipient/material lots and dispensing controls configurable. | Formulation trace. |
| INH-FR-005 | 56 | Powder blend | For DPI, blend/bulk powder properties/hold status and sampling/test links configurable. | DPI process. |
| INH-FR-006 | 56 | Component prep | Cleaning/handling/release of valves/canisters/actuators/blisters/capsules/device parts. | Readiness. |
| INH-FR-007 | 56 | Filling route | Configure pressure fill, cold fill, liquid fill, powder dose fill, blister/capsule fill or other released route. | Product-specific. |
| INH-FR-008 | 56 | Fill/dose controls | Target fill/dose, IPC sampling and weight/mass/reconciliation rules. | Dose quantity. |
| INH-FR-009 | 56 | Valve/crimp assembly | For MDI, capture valve placement, crimp dimensions/settings and leak/closure results. | Container closure. |
| INH-FR-010 | 56 | Device assembly | Actuator/device assembly with exact component lots and assembly program. | Device constituent. |
| INH-FR-011 | 56 | DPI dose unit loading | Track powder dose/blister/capsule lot and device association according to unit/lot architecture. | Genealogy. |
| INH-FR-012 | 56 | Leak/pressure test | Capture product-specific leak/pressure/closure integrity tests. | System integrity. |
| INH-FR-013 | 56 | Delivered dose | Support delivered-dose/uniformity test data and method/version where included in released spec. | Performance. |
| INH-FR-014 | 56 | Aerodynamic performance | Support cascade impaction/aerodynamic particle size distribution or other performance test result structures as product-specific QC methods. | Inhalation performance. |
| INH-FR-015 | 56 | Spray/plume pattern hooks | Support spray pattern/plume geometry or device-specific output tests when defined by control strategy. | Extensible. |
| INH-FR-016 | 56 | Priming/repriming | Device test profile can capture priming/repriming actuation requirements and results. | Use performance. |
| INH-FR-017 | 56 | Actuation count | MDI/DPI unit/device may track labeled actuations/doses and counter mechanism test where applicable. | Dose counter. |
| INH-FR-018 | 56 | Moisture/environment | DPI process can enforce humidity/environment readiness and excursion linkage. | Powder sensitivity. |
| INH-FR-019 | 56 | Blend/fill hold time | Track formulation/blend-to-filling and intermediate hold limits. | Validated timing. |
| INH-FR-020 | 56 | Cleaning/changeover | Product-contact line/device assembly area cleaning and line clearance required. | Cross-contamination. |
| INH-FR-021 | 56 | Sampling | Structured beginning/middle/end or configured location/time sampling plans. | Representativeness. |
| INH-FR-022 | 56 | Unit/lot inspection | Visual/device/pack integrity results and defects. | Finished quality. |
| INH-FR-023 | 56 | Packaging | Canister/device/capsule/blister + actuator/accessory/IFU/label/carton reconciliation. | Configuration. |
| INH-FR-024 | 56 | Genealogy | Drug formulation/blend + primary container/device lots → finished inhaler lot/unit. | Trace. |
| INH-FR-025 | 56 | OOS/OOT | Delivered dose/aerodynamic/device functional failures enter common OOS/OOT workflow and block release as configured. | Lab integrity. |
| INH-FR-026 | 56 | Constituent release | Drug/device constituent checkpoints remain separate from final inhaler release. | DDCP. |
| INH-FR-027 | 56 | Release blockers | Unresolved fill/closure/device/dose/aerodynamic/QMS/reconciliation issue blocks final release per profile. | No bypass. |
| INH-FR-028 | 56 | Stability linkage | Profile supports orientation/storage/stability sample references where product program requires. | Lifecycle. |
| INH-FR-029 | 56 | Change impact | Valve/canister/actuator/device material, formulation, propellant, fill/crimp/device program and test-method changes invoke Change/Risk/Validation. | Lifecycle. |
| INH-FR-030 | 56 | Draft guidance status | FDA 2018 MDI/DPI guidance is treated as nonbinding product-design input; customer released spec/control strategy governs executable requirements. | Correct regulatory handling. |
| COAT-FR-001 | 57 | Coated device profile | Support drug-eluting/coated/impregnated devices with device substrate + drug/biologic coating constituent + finished combined product. | Type 4/5 architecture. |
| COAT-FR-002 | 57 | Substrate identity | Track base device lot/serial/subassembly and released device specification/version. | Device constituent. |
| COAT-FR-003 | 57 | Drug/coating constituent | Track coating solution/formulation/bulk lot, concentration/potency, prepared amount and hold time. | Drug constituent. |
| COAT-FR-004 | 57 | Surface preparation | Capture cleaning/activation/priming/pre-treatment steps and evidence. | Coating readiness. |
| COAT-FR-005 | 57 | Coating recipe | Versioned coating process route: dip/spray/inkjet/deposition/impregnation/other approved method. | Extensible. |
| COAT-FR-006 | 57 | Coating parameters | Speed/time/flow/pressure/distance/temperature/humidity/cycle/pass and other mapped process parameters. | Process evidence. |
| COAT-FR-007 | 57 | Equipment/program | Coater/equipment and recipe/program version eligible and bound to batch. | Validated state. |
| COAT-FR-008 | 57 | Environment | Required room/temperature/humidity/particle/environment status gate. | Process control. |
| COAT-FR-009 | 57 | Drug usage ledger | Track drug/coating solution issued, applied, residual, sampled, rejected, recovered/disposed and reconcile. | Drug mass balance. |
| COAT-FR-010 | 57 | Unit/lot association | Map device lot/serial/substrate unit to coating run and drug/coating constituent lot. | Combination genealogy. |
| COAT-FR-011 | 57 | Coating weight/loading | Record direct/indirect drug loading/coating weight measurement according to approved method. | Dose/loading evidence. |
| COAT-FR-012 | 57 | Uniformity | Support coating thickness/loading/uniformity spatial or sampled result structures. | Quality. |
| COAT-FR-013 | 57 | Coating integrity | Inspection for delamination/cracks/defects/adhesion or product-specific attributes. | Device/drug interaction. |
| COAT-FR-014 | 57 | Drug content/assay | Link QC assay/content/impurity/degradation results for finished coated device where required. | Drug quality. |
| COAT-FR-015 | 57 | Release/elution profile | Support in-vitro release/elution test result sets when product specification requires. | Therapeutic performance. |
| COAT-FR-016 | 57 | Dimensional/device function | Ensure coating process does not invalidate required device dimensional/mechanical/functional tests. | Combined performance. |
| COAT-FR-017 | 57 | Drying/curing | Capture curing/drying conditions and hold times after coating. | Process. |
| COAT-FR-018 | 57 | Sterilization interaction | Profile specifies pre/post coating sterilization route and recognizes potential impact of sterilization on drug/coating/device. | Critical DDCP interaction. |
| COAT-FR-019 | 57 | Sterilization evidence | Link sterilization cycle/contract process to exact coated device lot/serial. | Genealogy. |
| COAT-FR-020 | 57 | Post-sterilization testing | Profile can require drug assay/degradation/release/device tests after sterilization. | Interaction verification. |
| COAT-FR-021 | 57 | Packaging | Barrier/package materials, protection, labeling and packaged lot genealogy. | Finished product. |
| COAT-FR-022 | 57 | Unit serialization | Support serial/unit-level coated device trace when device profile requires. | Device postmarket. |
| COAT-FR-023 | 57 | Process sampling | Sampling plan can select devices/locations/timepoints across coating run. | Representativeness. |
| COAT-FR-024 | 57 | OOS/NCR | Coating/drug/device failures create OOS/NCR/deviation and affected unit/lot scope. | QMS. |
| COAT-FR-025 | 57 | Rework | Recoating/stripping/reprocessing default prohibited unless released validated route explicitly permits and drug/device impact assessed. | Safe default. |
| COAT-FR-026 | 57 | Yield/reconciliation | Reconcile device units and drug/coating material separately and combined. | Full balance. |
| COAT-FR-027 | 57 | Constituent checkpoints | Device substrate and drug constituent may have separate release inputs; finished coated device has independent final release. | Part 4. |
| COAT-FR-028 | 57 | Final blockers | Coating parameter excursion, drug reconciliation gap, sterilization issue, assay/release/device failure, genealogy gap or QMS issue blocks release. | No bypass. |
| COAT-FR-029 | 57 | Change impact | Substrate material, coating formulation, drug source, coating equipment/program, environment, sterilization, packaging and test-method changes require Change/Risk/Validation assessment. | Lifecycle. |
| COAT-FR-030 | 57 | Complaint/field trace | Complaint serial/lot can trace backward to coating run/drug lot and forward to affected distributed units. | Postmarket. |
