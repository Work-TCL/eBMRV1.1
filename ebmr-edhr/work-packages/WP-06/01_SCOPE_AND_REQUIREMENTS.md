# WP-06 — Scope & Requirements

**In scope:** Documents 38, 39, 40, 41, 42, 43, 44, 45, 46, 47

## Document 38 — Equipment, Calibration, Qualification & Maintenance (SPEC-EQP-001)

- Code location: `services/gxp-api/src/modules/equipment`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: EQP-FR-001..030 (30)

## Document 39 — Cleaning, Sanitization & Line Clearance (SPEC-EQP-002)

- Code location: `services/gxp-api/src/modules/equipment`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: CLN-FR-001..028 (28)

## Document 40 — Sterile / Aseptic Manufacturing Operations (SPEC-EQP-003)

- Code location: `services/gxp-api/src/modules/equipment`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: ASP-FR-001..028 (28)

## Document 41 — Environmental Monitoring & Cleanroom State Control (SPEC-EQP-004)

- Code location: `services/gxp-api/src/modules/equipment`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: EM-FR-001..026 (26)

## Document 42 — Sterilization, CIP/SIP & Sterile Filtration Management (SPEC-EQP-005)

- Code location: `services/gxp-api/src/modules/equipment`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: STR-FR-001..030 (30)

## Document 43 — Edge Gateway Runtime Architecture & Construction Specification (SPEC-EDGE-001)

- Code location: `edge`
- Authoritative store: Edge local store (buffered, pre-authoritative) → PostgreSQL on acceptance
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: EDGE-FR-001..030 (30)

## Document 44 — Industrial Device & Protocol Connectivity / Driver Specification (SPEC-EDGE-002)

- Code location: `edge`
- Authoritative store: Edge local store (buffered, pre-authoritative) → PostgreSQL on acceptance
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: DRV-FR-001..025 (25)

## Document 45 — Store-and-Forward, Offline Buffering, Time Integrity & Data Quality (SPEC-EDGE-003)

- Code location: `edge`
- Authoritative store: Edge local store (buffered, pre-authoritative) → PostgreSQL on acceptance
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: BUF-FR-001..030 (30)

## Document 46 — Barcode, Scanner, Balance, Printer, Tester & Peripheral Integration (SPEC-EDGE-004)

- Code location: `edge`
- Authoritative store: Edge local store (buffered, pre-authoritative) → PostgreSQL on acceptance
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: PER-FR-001..025 (25)

## Document 47 — Machine / PLC / SCADA Data Acquisition, Evidence Mapping & Command Boundary (SPEC-EDGE-005)

- Code location: `edge`
- Authoritative store: Edge local store (buffered, pre-authoritative) → PostgreSQL on acceptance
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: MAP-FR-001..032 (32)

## All requirements

| ID | Doc | Requirement | Behaviour | Acceptance |
|---|---|---|---|---|
| EQP-FR-001 | 38 | Equipment master | Unique asset ID, type/class, manufacturer/model/serial, site/area/location, ownership and lifecycle status. | Canonical equipment identity. |
| EQP-FR-002 | 38 | Equipment class | Reusable equipment class defines capability, process use, calibration/maintenance/cleaning requirements and allowed recipe roles. | Recipe compatibility. |
| EQP-FR-003 | 38 | Lifecycle | Planned, Installed, Qualification Pending, Qualified/Available, Maintenance, Calibration Due, Out of Service, Suspended, Retired. | Explicit state. |
| EQP-FR-004 | 38 | Qualification status | Track IQ/OQ/PQ or equivalent qualification references, approved scope, effective/expiry/requalification triggers. | Use only qualified assets. |
| EQP-FR-005 | 38 | Calibration plan | Define calibration points, tolerances, procedure/version, frequency, standard requirements and due rules. | Controlled calibration. |
| EQP-FR-006 | 38 | Calibration execution | Capture pre-calibration/as-found, adjustments, post-calibration/as-left, standard/equipment, performer, date and result. | Complete evidence. |
| EQP-FR-007 | 38 | Out-of-tolerance calibration | OOT calibration automatically generates equipment hold/impact assessment and may trigger deviation/CAPA. | Product impact controlled. |
| EQP-FR-008 | 38 | Calibration standards | Reference standard/tool ID, calibration status, traceability/evidence and expiry. | Reliable calibration. |
| EQP-FR-009 | 38 | Preventive maintenance plan | Frequency, tasks, parts, procedure, owner, expected downtime and due dates. | Routine upkeep. |
| EQP-FR-010 | 38 | Maintenance work order | Create planned/corrective work order with fault, work, parts, technician, timestamps and verification. | Service history. |
| EQP-FR-011 | 38 | Post-maintenance verification | Equipment remains unavailable until required inspection/calibration/requalification/cleaning complete. | Safe return. |
| EQP-FR-012 | 38 | Breakdown | Unexpected failure marks equipment unavailable and evaluates affected in-process/recent batches. | Impact. |
| EQP-FR-013 | 38 | Equipment use log | Record date/time, batch/product/operation, operator/source, cleaning/maintenance context in chronological history. | 211.182 support. |
| EQP-FR-014 | 38 | Dedicated equipment | Support dedicated-equipment profile with use/cleaning evidence in batch when appropriate. | Flexible compliance. |
| EQP-FR-015 | 38 | Pre-use eligibility | Batch step checks current qualification, calibration, maintenance, cleaning and hold status. | No invalid equipment. |
| EQP-FR-016 | 38 | Reservation | Reserve equipment for batch/time window; reservation never overrides quality eligibility. | Scheduling. |
| EQP-FR-017 | 38 | Meter/runtime counters | Capture hours/cycles/counts from Edge/manual source for condition/frequency-based maintenance. | Predictive scheduling. |
| EQP-FR-018 | 38 | Instrument/device identity | Register PLC, balance, tester, sensor, controller or machine endpoints and credentials/certificates separately from asset master. | Secure integration. |
| EQP-FR-019 | 38 | Edge mapping | Versioned mapping between equipment tag/channel and GxP parameter. | Source traceability. |
| EQP-FR-020 | 38 | Status from maintenance system | External CMMS can provide work-order/reference status, but final GxP availability uses controlled product policy. | Boundary. |
| EQP-FR-021 | 38 | Spare parts | Record critical replaced component/part/serial where product/process impact exists. | Maintenance evidence. |
| EQP-FR-022 | 38 | Change control | Critical equipment modification links Change Control and validation impact. | Validated state. |
| EQP-FR-023 | 38 | Software/firmware | Track firmware/software/config version for automated equipment where relevant. | Reproducibility. |
| EQP-FR-024 | 38 | Alarm/events | Equipment alarms linked to batch/step and deviation when released rules require. | Process impact. |
| EQP-FR-025 | 38 | Cleaning dependency | Eligibility references current cleaning/sanitization/sterilization state from Document 39/42. | Integrated. |
| EQP-FR-026 | 38 | Location transfer | Moving equipment to another area/site can trigger requalification/change/cleaning requirements. | Controlled relocation. |
| EQP-FR-027 | 38 | Retirement | Retire with final status, data retention, outstanding batch/maintenance impact and approval. | Lifecycle closure. |
| EQP-FR-028 | 38 | Dashboard | Due calibration/maintenance, out-of-service, utilization, recurring failures and impact events. | Operational visibility. |
| EQP-FR-029 | 38 | Audit/export | Complete qualification/calibration/maintenance/use history exportable. | Inspection-ready. |
| EQP-FR-030 | 38 | No status bypass | Admin/operator cannot manually set 'Qualified/Available' without controlled evidence/authority. | Integrity. |
| CLN-FR-001 | 39 | Cleaning procedure | Released procedure by equipment/area/product family defining method, agent, concentration, contact time, tools, disassembly/reassembly and acceptance. | Controlled method. |
| CLN-FR-002 | 39 | Cleaning type | Routine, product-changeover, campaign-end, deep clean, sanitization, manual, COP/CIP reference. | Clear semantics. |
| CLN-FR-003 | 39 | Schedule | Time/use/campaign/batch-count triggered cleaning due rules. | Appropriate intervals. |
| CLN-FR-004 | 39 | Responsibility | Procedure defines performer/verifier roles and qualifications. | 211.67 support. |
| CLN-FR-005 | 39 | Previous batch identity removal | Checklist/evidence confirms removal/obliteration of prior product/batch labels/materials/documents. | Mix-up prevention. |
| CLN-FR-006 | 39 | Pre-clean status | Equipment/area placed Dirty/To Clean and unavailable for use. | Execution gate. |
| CLN-FR-007 | 39 | Cleaning execution | Capture procedure version, agents/lots, concentration, times, steps, performer/source and evidence. | Complete record. |
| CLN-FR-008 | 39 | Disassembly/reassembly | Required components/parts tracked and verification before release. | Proper cleaning. |
| CLN-FR-009 | 39 | Inspection | Immediate pre-use cleanliness inspection where applicable, separate from cleaning completion. | 211.67 support. |
| CLN-FR-010 | 39 | Swab/rinse sampling | Where validation/routine verification requires, create QC sample/test with location/limit/spec. | Analytical verification. |
| CLN-FR-011 | 39 | Visual acceptance | Structured inspection criteria/results; visual-only permitted only where approved procedure allows. | Controlled. |
| CLN-FR-012 | 39 | Dirty hold time | Track maximum allowed time from use to cleaning start and generate deviation if exceeded. | Validated limits. |
| CLN-FR-013 | 39 | Clean hold time | Track clean state expiry; expired equipment requires re-clean/reinspection per procedure. | Protected clean state. |
| CLN-FR-014 | 39 | Protection after cleaning | Record cover/closure/storage state to protect clean equipment before use. | 211.67 support. |
| CLN-FR-015 | 39 | Cleaning verification failure | Failed swab/rinse/visual check creates deviation/NCR and equipment remains unavailable. | Fail safe. |
| CLN-FR-016 | 39 | Line clearance plan | Released checklist by line/area/process/packaging step. | Consistent clearance. |
| CLN-FR-017 | 39 | Line clearance execution | Verify removal of prior materials/components/labels/documents/product and readiness of area/equipment. | Mix-up prevention. |
| CLN-FR-018 | 39 | Material/label clearance | Scan/count leftover material/labels and reconcile/return/destroy as applicable. | Packaging integration. |
| CLN-FR-019 | 39 | Equipment status clearance | Confirm correct cleaned/calibrated/qualified equipment installed. | Readiness. |
| CLN-FR-020 | 39 | Area status | Confirm room/line cleanliness/environmental readiness and no incompatible concurrent operation. | Contamination control. |
| CLN-FR-021 | 39 | Independent verification | Second-person/automated verification where procedure requires. | Authority. |
| CLN-FR-022 | 39 | Batch linkage | Line clearance and cleaning evidence linked to exact batch/stage/packaging run. | eBMR evidence. |
| CLN-FR-023 | 39 | Changeover | End-of-batch clearance and next-product startup clearance remain distinct records. | No ambiguous state. |
| CLN-FR-024 | 39 | Campaign rules | Campaign manufacturing allows defined cleaning frequency but records each use and campaign boundary. | Configurable. |
| CLN-FR-025 | 39 | Automated cleaning | CIP/SIP cycle may satisfy parts of cleaning record only through validated interface and verification. | Automation safe. |
| CLN-FR-026 | 39 | Cleaning validation reference | Procedure references current approved validation study/matrix and product/equipment family applicability. | Validated basis. |
| CLN-FR-027 | 39 | Cleaning status | Equipment/area states: DIRTY, CLEANING, CLEAN, CLEAN_EXPIRED, HOLD, READY_FOR_USE. | Explicit. |
| CLN-FR-028 | 39 | Audit/export | Chronological cleaning/use/inspection/line-clearance history exportable. | Inspection-ready. |
| ASP-FR-001 | 40 | Sterile product profile | Product/recipe references released sterile/aseptic profile defining applicable controls. | Profile driven. |
| ASP-FR-002 | 40 | Classified area | Define cleanroom/zone/critical area and approved operation types. | Area eligibility. |
| ASP-FR-003 | 40 | Personnel qualification | Gowning/aseptic technique/media-fill or process qualification required by role/operation. | Qualified personnel. |
| ASP-FR-004 | 40 | Area qualification | Room/zone qualification/status required before aseptic operation. | Facility state. |
| ASP-FR-005 | 40 | Environmental readiness | Current EM/HVAC/pressure/temp/humidity status evaluated before start. | Controlled environment. |
| ASP-FR-006 | 40 | Line/room clearance | Required cleaning/disinfection/line-clearance complete before setup. | Readiness. |
| ASP-FR-007 | 40 | Sterile component status | Components, containers/closures, tools and product-contact parts must have valid sterile/clean status. | No contaminated input. |
| ASP-FR-008 | 40 | Equipment sterilization status | Applicable equipment/SIP/autoclave/filter status verified before use. | Sterility assurance. |
| ASP-FR-009 | 40 | Aseptic setup | Record assembly/setup steps, operators, sterile connections, equipment and timestamps. | Setup trace. |
| ASP-FR-010 | 40 | Intervention catalogue | Versioned catalogue: inherent/routine/corrective/non-routine interventions with permitted method and risk. | Structured interventions. |
| ASP-FR-011 | 40 | Intervention execution | Record exact time, operator, location, reason, duration, impacted units/time window and evidence. | Batch impact. |
| ASP-FR-012 | 40 | Unplanned intervention | Creates deviation/quality assessment based on rule. | No hidden intervention. |
| ASP-FR-013 | 40 | Open exposure time | Track exposure/hold time of sterile components/product when procedure defines limit. | Time control. |
| ASP-FR-014 | 40 | Aseptic process hold times | Bulk/filter/filling/stoppering/sealing hold times monitored and enforced. | Validated limits. |
| ASP-FR-015 | 40 | Filling operation | Capture line/filler, speed, fill parameters, batch/fill group, operators and machine data. | Complete process. |
| ASP-FR-016 | 40 | Container closure operation | Capture stoppering/sealing/capping status and inspection evidence. | Closure control. |
| ASP-FR-017 | 40 | Reject management | Aseptic/filling rejects tracked with reason, counts, serial/container range where applicable. | Reconciliation. |
| ASP-FR-018 | 40 | Media-fill qualification reference | Associate line/personnel/process qualification evidence and current status; full media-fill execution may be child spec. | Process assurance. |
| ASP-FR-019 | 40 | Sterility/bioburden tests | Link relevant QC test orders/results and release blockers. | Lab integration. |
| ASP-FR-020 | 40 | Filter integrity | Reference pre/post-use filter integrity requirement/result where configured. | Filtration assurance. |
| ASP-FR-021 | 40 | Environmental excursion | EM/HVAC/pressure excursion during operation creates impact window and Quality event. | Batch impact. |
| ASP-FR-022 | 40 | Operator excursion | Loss of qualification/gown breach/critical intervention creates hold/assessment. | Personnel risk. |
| ASP-FR-023 | 40 | RABS/isolator profile | Support barrier system identity, decontamination cycle status, glove integrity and intervention mapping when used. | Modern aseptic operations. |
| ASP-FR-024 | 40 | Gowning entry | Optional access/gowning qualification confirmation at area entry for regulated execution. | Access control. |
| ASP-FR-025 | 40 | Batch impact timeline | Overlay interventions, EM excursions, alarms and process events on manufacturing timeline. | Review-by-exception. |
| ASP-FR-026 | 40 | Aseptic completion | Operation cannot complete until sterile inputs, interventions, counts, EM and required process evidence resolved/current. | Completeness. |
| ASP-FR-027 | 40 | QA review | Aseptic summary feeds Review-by-Exception and Release Engine. | Release control. |
| ASP-FR-028 | 40 | Audit/export | Full aseptic execution package exportable with interventions, environment, sterile status and signatures. | Inspection-ready. |
| EM-FR-001 | 41 | EM program | Released program by site/area defining locations, methods, frequencies, shifts/operations, limits and actions. | Written program. |
| EM-FR-002 | 41 | Location master | Unique monitoring point with room/zone, coordinates/description, sample type and criticality. | Exact location. |
| EM-FR-003 | 41 | Monitoring types | Viable air, surface/contact, settle plate, personnel, nonviable particles, temperature, humidity, differential pressure and other approved types. | Comprehensive. |
| EM-FR-004 | 41 | Schedule | Routine/static/dynamic/in-operation/post-operation schedules and event-triggered monitoring. | Coverage. |
| EM-FR-005 | 41 | Sample plan | Create EM sampling tasks with location/method/media/instrument/assigned qualified user. | Execution. |
| EM-FR-006 | 41 | Instrument eligibility | Particle counter/sensor/air sampler must be calibrated/qualified. | Valid source. |
| EM-FR-007 | 41 | Media/reagent | Microbiological media lot/status/growth-promotion/expiry where applicable. | Microbiology integrity. |
| EM-FR-008 | 41 | Sample execution | Capture collector, actual location/time, operation/batch context, instrument/media and conditions. | Trace. |
| EM-FR-009 | 41 | Incubation | Track media incubation conditions/times and readings for viable monitoring. | Complete microbiology. |
| EM-FR-010 | 41 | Result | Structured count/value/qualitative result and units; raw evidence retained. | Data. |
| EM-FR-011 | 41 | Alert/action limits | Versioned limits by location/type/state/operation; distinction between alert and action. | Controlled thresholds. |
| EM-FR-012 | 41 | Excursion trigger | Limit excursion creates EM event/deviation/investigation and relevant area/batch impact. | Fail safe. |
| EM-FR-013 | 41 | Organism identification | Support organism ID/species/genus/gram/morphology or lab reference where required. | Microbial investigation. |
| EM-FR-014 | 41 | Personnel monitoring | Link result to operator/gowning session/aseptic operation while respecting access/privacy. | Personnel impact. |
| EM-FR-015 | 41 | Continuous sensors | HVAC/BMS sensors integrate via Edge; retain source identity, timestamps, quality and evidence summaries. | Automation. |
| EM-FR-016 | 41 | Data gap | Missing/failed sensor/sample task creates data-gap event; no silent interpolation for GxP decision. | Integrity. |
| EM-FR-017 | 41 | Trend | Trend by location/type/organism/shift/product/season/time and detect deterioration before action limits. | State of control. |
| EM-FR-018 | 41 | Baseline | Trend baseline/version/cutoff retained. | Reproducible. |
| EM-FR-019 | 41 | Batch correlation | Associate dynamic/in-operation results and excursions to exact batch/stage/time window. | Impact assessment. |
| EM-FR-020 | 41 | Area status | Area readiness derives from current program/tasks/excursions/HVAC state, not manual green flag. | Execution gate. |
| EM-FR-021 | 41 | Investigation | Excursion links Deviation/CAPA and cleaning/disinfection corrective action. | QMS. |
| EM-FR-022 | 41 | Resampling | Resampling after excursion is controlled and does not erase original excursion. | No testing into compliance. |
| EM-FR-023 | 41 | Facility alarms | Pressure/temp/humidity/particle alarm events included in batch/QA timeline where relevant. | Review. |
| EM-FR-024 | 41 | Review | Microbiology/QA review results and trends; signatures according to procedure. | Authority. |
| EM-FR-025 | 41 | Retention/export | Raw result/evidence, trend and excursion history retained/exportable. | Inspection-ready. |
| EM-FR-026 | 41 | Performance | Continuous high-frequency raw telemetry stays historian/time-series; GxP store keeps relevant event/result/evidence refs. | Scale. |
| STR-FR-001 | 42 | Process profile | Released sterilization/CIP/SIP/filter process profile by equipment/product/component/load type. | Validated recipe. |
| STR-FR-002 | 42 | Process types | Steam/autoclave, dry heat, depyrogenation, gas/radiation/external reference, SIP, CIP, sterile filtration and approved future types. | Extensible. |
| STR-FR-003 | 42 | Cycle recipe version | Exact cycle parameters, phases, limits, sensors and acceptance rules Vault-released. | No controller drift. |
| STR-FR-004 | 42 | Load definition | Record load items, equipment/parts/components, lot/container IDs, load configuration and pattern version. | Load trace. |
| STR-FR-005 | 42 | Equipment eligibility | Sterilizer/CIP/SIP system must be qualified/calibrated/maintained and correct recipe available. | Valid equipment. |
| STR-FR-006 | 42 | Cycle start authorization | Verify load, recipe, operator, equipment and prerequisites before start. | Prevention. |
| STR-FR-007 | 42 | Automated cycle acquisition | Capture controller/PLC cycle ID, parameters, alarms, phase data, source timestamps, quality and evidence file. | Raw process evidence. |
| STR-FR-008 | 42 | Critical parameter evaluation | Released rule checks temperature/pressure/time/F0/concentration/flow/conductivity or process-specific parameters. | Deterministic acceptance. |
| STR-FR-009 | 42 | Cycle deviation | Critical excursion/alarm automatically fails/holds cycle pending investigation; operator cannot manually mark pass. | Fail safe. |
| STR-FR-010 | 42 | Cycle review | Qualified reviewer assesses cycle/evidence/alarms and signs acceptance/rejection. | Independent. |
| STR-FR-011 | 42 | Biological/chemical indicators | Where used, record indicator IDs/locations/lots/results and QC links. | Validation/routine evidence. |
| STR-FR-012 | 42 | Sterile status issuance | Accepted sterilization cycle grants bounded sterile status to exact load items with expiry/hold rules. | Downstream eligibility. |
| STR-FR-013 | 42 | SIP status | Accepted SIP grants equipment/product-contact path sterile status for defined validity window. | Aseptic readiness. |
| STR-FR-014 | 42 | CIP execution | Record cleaning solution, concentration, temperature, flow, time, conductivity/rinse endpoints and alarms. | Automated cleaning. |
| STR-FR-015 | 42 | CIP verification | CIP completion may still require sampling/visual/chemical verification per procedure. | No automation shortcut. |
| STR-FR-016 | 42 | Filter master | Filter type/manufacturer/lot/serial/pore rating/application/install location/status. | Exact identity. |
| STR-FR-017 | 42 | Filter installation | Record filter lot/serial, housing, direction, operator, sterilization/status and product/batch use. | Genealogy. |
| STR-FR-018 | 42 | Pre-use integrity test | Where profile requires, perform/record approved integrity test before use. | Filter assurance. |
| STR-FR-019 | 42 | Post-use integrity test | Where required, perform/record after filtration and before release decision. | Process assurance. |
| STR-FR-020 | 42 | Integrity failure | Failure creates batch/equipment hold, deviation and impacted product assessment; original result retained. | No hidden failure. |
| STR-FR-021 | 42 | Filtration parameters | Record pressure/flow/differential pressure/time/volume/temp and filter train as required. | Complete process. |
| STR-FR-022 | 42 | Filter reuse | Default single-use unless released validated profile explicitly permits reuse with cycle/use tracking. | Safe default. |
| STR-FR-023 | 42 | Vent/gas filters | Support sterile gas/vent filter identity, sterilization and integrity where applicable. | Barrier control. |
| STR-FR-024 | 42 | Hold-time link | Sterilized item/filter/clean equipment validity ties to aseptic/clean hold limits. | Integrated. |
| STR-FR-025 | 42 | External sterilizer | Contract sterilization adapter can import cycle/load/certificate/evidence but Quality acceptance remains GxP-controlled. | Supplier boundary. |
| STR-FR-026 | 42 | Reprocessing after failure | Failed cycle cannot simply be rerun; approved investigation/reprocessing route required. | No test-until-pass. |
| STR-FR-027 | 42 | Qualification/validation reference | Cycle profile references approved validation/requalification evidence and load pattern. | Validated basis. |
| STR-FR-028 | 42 | Batch/device genealogy | Sterilization/filter/cycle relationships appear in genealogy/eDHR/eBMR. | Trace. |
| STR-FR-029 | 42 | QA/release integration | Unreviewed/failed required cycle or filter integrity blocks QA/release. | Release control. |
| STR-FR-030 | 42 | Audit/export | Cycle/load/filter/raw evidence/review/impact package exportable. | Inspection-ready. |
| EDGE-FR-001 | 43 | Gateway identity | Every gateway has immutable gateway ID, tenant/site assignment, host identity, certificate and lifecycle state. | No anonymous edge. |
| EDGE-FR-002 | 43 | Enrollment | New gateway enrollment requires one-time bootstrap token or administrator-approved enrollment and results in device certificate/workload identity. | Controlled onboarding. |
| EDGE-FR-003 | 43 | Site isolation | Gateway configuration and outbound data are bound to one authorized tenant/site deployment context unless an explicitly approved multi-site design exists. | No cross-tenant leakage. |
| EDGE-FR-004 | 43 | Configuration versions | Connector, mapping, certificate, buffering and forwarding configuration is immutable/versioned; gateway applies exact approved config version. | Reproducible runtime. |
| EDGE-FR-005 | 43 | Config validation | Gateway validates schema, signatures/checksum, supported plugin versions and contradictory settings before activation. | Bad config rejected. |
| EDGE-FR-006 | 43 | Atomic config activation | New configuration activates atomically; on failure gateway retains prior valid configuration and reports failure. | No half-configured runtime. |
| EDGE-FR-007 | 43 | Connector supervision | Gateway starts/stops/restarts drivers under supervisor and isolates crashing connector from other connectors. | Fault containment. |
| EDGE-FR-008 | 43 | Plugin sandbox boundary | Protocol plugins expose fixed adapter interfaces and cannot access GxP database credentials or unrestricted filesystem/secrets. | Security boundary. |
| EDGE-FR-009 | 43 | Observation envelope | All readings/events normalize into canonical EdgeObservationEnvelope before buffering/forwarding. | Common downstream contract. |
| EDGE-FR-010 | 43 | Source provenance | Envelope carries gateway, connector, device, source address/tag/node/register, mapping version and source event identity. | Traceable source. |
| EDGE-FR-011 | 43 | Timestamp model | Envelope carries source timestamp, gateway receive timestamp, UTC normalization and clock-quality metadata. | Chronology explicit. |
| EDGE-FR-012 | 43 | Data quality | Every observation includes quality/status such as GOOD, UNCERTAIN, BAD, STALE, COMM_ERROR, CLOCK_UNCERTAIN, MANUAL_FALLBACK. | No silent bad data. |
| EDGE-FR-013 | 43 | Canonical units | Mappings may convert source units to canonical units only through versioned conversion rule; raw source value/unit retained where required. | Reproducibility. |
| EDGE-FR-014 | 43 | Local buffering | Every forward-required observation/event is durably buffered before network transmission according to Document 45. | Loss resistance. |
| EDGE-FR-015 | 43 | Delivery acknowledgement | Gateway removes/archives delivery item only after authoritative server acknowledgement of exact event ID/range. | At-least-once safe. |
| EDGE-FR-016 | 43 | Idempotency | Globally unique event ID + gateway sequence prevents duplicate GxP effects during retries. | Replay safe. |
| EDGE-FR-017 | 43 | Health reporting | Gateway reports host, storage, buffer age/depth, connector status, clock health, certificate expiry, CPU/memory and version. | Operable. |
| EDGE-FR-018 | 43 | Local health UI/API | Authorized support can inspect status/config version without exposing secrets or modifying regulated mapping casually. | Supportable. |
| EDGE-FR-019 | 43 | Remote update | Software/plugin update is signed/versioned, change-controlled and supports rollback; no auto-update of validated production gateways by default. | Controlled SDLC. |
| EDGE-FR-020 | 43 | Certificate rotation | Rotate gateway/client certificates before expiry without changing gateway identity. | Secure lifecycle. |
| EDGE-FR-021 | 43 | Secrets | Secrets stored via OS/key store/secret file with restrictive permissions; never committed in config repo or logs. | Credential safety. |
| EDGE-FR-022 | 43 | Network segmentation | Gateway supports industrial-side and enterprise/cloud-side network interfaces with outbound-only preferred architecture. | Reduced attack surface. |
| EDGE-FR-023 | 43 | Command channel | Inbound machine command channel disabled by default; enabled only for explicit approved command profiles with allowlist and local safety interlocks. | Safe default. |
| EDGE-FR-024 | 43 | Local continuity | If upstream unavailable, acquisition and buffer continue while disk capacity policy permits. | Plant resilience. |
| EDGE-FR-025 | 43 | Disk pressure | Buffer thresholds trigger warning/critical alarms and documented degradation policy; silent data deletion prohibited. | Capacity safety. |
| EDGE-FR-026 | 43 | Clock health | Gateway monitors NTP/PTP/system clock offset; degraded clock marks data quality rather than rewriting source time silently. | Time integrity. |
| EDGE-FR-027 | 43 | Audit/config history | Gateway/server preserve enrollment, config activation, plugin update, certificate rotation and security-relevant runtime events. | Inspection/support trace. |
| EDGE-FR-028 | 43 | Observability | Structured logs, metrics and traces use correlation IDs and redact credentials/raw secrets. | Operations. |
| EDGE-FR-029 | 43 | Container deployment | Reference deployment supports signed container images/systemd/container runtime with restart policy and health probes. | Repeatable deployment. |
| EDGE-FR-030 | 43 | No local business truth | Gateway never independently marks batch step, QC result, equipment calibration or product release as complete. | Trust boundary. |
| DRV-FR-001 | 44 | Driver interface | All protocol plugins implement common lifecycle/connect/read/subscribe/write-capability/health contract. | Uniform runtime. |
| DRV-FR-002 | 44 | OPC UA endpoint | Support endpoint discovery/configured URL, security policy/mode, certificate trust and user/application authentication. | Secure OPC UA. |
| DRV-FR-003 | 44 | OPC UA certificates | Application instance certificate and trusted/rejected certificate stores managed explicitly. | Identity. |
| DRV-FR-004 | 44 | OPC UA browse | Authorized engineering mode may browse namespaces/nodes for mapping; production mapping references exact NodeIds. | Stable mapping. |
| DRV-FR-005 | 44 | OPC UA subscriptions | Support monitored items, sampling/publishing interval, queue size and reconnect/resubscribe. | Efficient acquisition. |
| DRV-FR-006 | 44 | OPC UA status | Map UA StatusCode/source/server timestamps into canonical quality/time fields. | Quality preserved. |
| DRV-FR-007 | 44 | Modbus TCP | Support host/unit ID/function/register/type/endianness/scaling with bounded polling. | Common industrial. |
| DRV-FR-008 | 44 | Modbus RTU | Support serial port/baud/parity/stop bits/slave ID/register mapping and bus serialization. | Serial support. |
| DRV-FR-009 | 44 | Modbus invalid value | Timeout/CRC/exception/out-of-range marks BAD/COMM_ERROR; never substitute last good as current without STALE quality. | Integrity. |
| DRV-FR-010 | 44 | MQTT 5 | Support broker TLS/auth, topic filters, QoS policy, retained flag handling, payload schema/version and client session policy. | Message source. |
| DRV-FR-011 | 44 | MQTT payload validation | JSON/binary/custom payload decoded only through versioned decoder plugin/schema. | No arbitrary parsing. |
| DRV-FR-012 | 44 | SNMP | Support v3 preferred with scoped credentials, OID mapping and polling/trap profile where appropriate. | Utilities/UPS. |
| DRV-FR-013 | 44 | Generic TCP/serial | Custom proprietary protocol lives in isolated adapter with framing/checksum/test vectors. | Extensibility. |
| DRV-FR-014 | 44 | REST/file adapter | Support authenticated REST polling/webhook or controlled file import for instruments producing reports. | Instrument integration. |
| DRV-FR-015 | 44 | Connection retry | Exponential backoff/jitter with configured max and health state; avoid network storms. | Resilience. |
| DRV-FR-016 | 44 | Source rate limits | Per-device poll/subscription limits prevent overloading PLC/instrument. | Operational safety. |
| DRV-FR-017 | 44 | Read/write separation | Driver advertises read/write capability separately; runtime blocks write unless explicit command profile. | Safe default. |
| DRV-FR-018 | 44 | Mapping test | Engineering test reads source and displays raw/normalized preview without committing regulated result. | Safe commissioning. |
| DRV-FR-019 | 44 | Simulation | Provide deterministic simulator/mock driver for CI/validation. | Testability. |
| DRV-FR-020 | 44 | Driver version | Every observation carries driver/plugin version. | Reproducibility. |
| DRV-FR-021 | 44 | Reconnect sequence | After reconnect, driver resubscribes/restarts polling and emits gap/reconnect event. | Data-gap awareness. |
| DRV-FR-022 | 44 | Credential rotation | Connector secrets/certs can rotate without rewriting mapping. | Security. |
| DRV-FR-023 | 44 | Driver health | Connection state, last success, error count, latency and source-specific diagnostics. | Observability. |
| DRV-FR-024 | 44 | Protocol errors | Native errors normalized to stable driver error taxonomy while raw diagnostic retained. | Support. |
| DRV-FR-025 | 44 | Production configuration | Protocol mapping config released/versioned; ad-hoc runtime node/register edits prohibited. | Validated state. |
| BUF-FR-001 | 45 | Durable append | Canonical envelope is written durably before first upstream send. | No transient loss. |
| BUF-FR-002 | 45 | Sequence | Gateway assigns strictly monotonic local sequence within gateway identity. | Order trace. |
| BUF-FR-003 | 45 | Unique event | Event ID globally unique and immutable. | Idempotency. |
| BUF-FR-004 | 45 | Payload hash | Persist SHA-256 or approved digest of canonical payload. | Integrity. |
| BUF-FR-005 | 45 | WAL/recovery | Reference SQLite WAL startup integrity check and crash recovery. | Restart safe. |
| BUF-FR-006 | 45 | Delivery states | PENDING, IN_FLIGHT, ACKED, REJECTED_REVIEW, PURGE_ELIGIBLE. | Explicit. |
| BUF-FR-007 | 45 | Batch sending | Forward ordered batches bounded by count/bytes. | Efficient. |
| BUF-FR-008 | 45 | Acknowledgement | Server ack identifies exact event IDs/ranges and accepted/duplicate/rejected disposition. | Deterministic. |
| BUF-FR-009 | 45 | Retry | Unacknowledged items retry with exponential backoff/jitter. | Resilient. |
| BUF-FR-010 | 45 | Duplicate handling | Server duplicate ack considered delivered when payload hash matches same event ID. | Replay safe. |
| BUF-FR-011 | 45 | Conflict handling | Same event ID with different payload hash is security/data-integrity incident. | Tamper detection. |
| BUF-FR-012 | 45 | Network outage | Continue acquisition until configured local storage thresholds. | Continuity. |
| BUF-FR-013 | 45 | Disk watermarks | Warning/critical/emergency thresholds and alarms. | Capacity. |
| BUF-FR-014 | 45 | Purge | Only ACKED data beyond local retention may purge automatically. | No unacked deletion. |
| BUF-FR-015 | 45 | Large evidence | Large files use content-addressed store and separate manifest/outbox event. | Scale. |
| BUF-FR-016 | 45 | Clock metadata | Buffer never modifies source timestamp to make delayed data appear current. | Integrity. |
| BUF-FR-017 | 45 | Late data | Server receives source time and receive time; downstream rules decide applicability. | Controlled. |
| BUF-FR-018 | 45 | Freshness | Stale/late quality can be computed without deleting original observation. | Truth. |
| BUF-FR-019 | 45 | Gap detection | Gateway/server detect missing sequence ranges and report gap. | Completeness. |
| BUF-FR-020 | 45 | Rejected payload | Schema/mapping rejection retained for admin reconciliation; not silently dropped. | Recoverable. |
| BUF-FR-021 | 45 | Manual replay | Authorized admin can replay exact original envelope; replay reason/audit captured. | Controlled support. |
| BUF-FR-022 | 45 | Backfill | Bulk historical backfill uses same idempotency/validation but separately tagged BACKFILL. | Clear semantics. |
| BUF-FR-023 | 45 | Compression | Network batching/compression allowed without changing canonical hash semantics. | Efficiency. |
| BUF-FR-024 | 45 | Encryption | Local disk/volume encryption and TLS in transit. | Security. |
| BUF-FR-025 | 45 | Retention policy | Per site/evidence type local retention and max horizon configurable, but unacked purge forbidden. | Governed. |
| BUF-FR-026 | 45 | Integrity scan | Periodic check verifies payload hashes/content-addressed evidence. | Tamper detection. |
| BUF-FR-027 | 45 | Backup not required for transient buffer | Gateway buffer is resilient queue, not substitute for authoritative server backup; deployment may snapshot if needed. | Boundary. |
| BUF-FR-028 | 45 | Metrics | Depth, oldest pending age, send rate, retry rate, rejected count, disk usage. | Operations. |
| BUF-FR-029 | 45 | Power loss | Uncommitted records must not appear delivered; committed rows recover after abrupt power loss. | Crash consistency. |
| BUF-FR-030 | 45 | No order dependency assumption | Server uses event IDs/timestamps/sequence but business logic must tolerate late/out-of-order arrival when documented. | Distributed resilience. |
| PER-FR-001 | 46 | Peripheral registry | Barcode scanners, balances, printers, testers, cameras/vision and other peripherals have registered identity and site/station assignment. | Attributable source. |
| PER-FR-002 | 46 | Station profile | Define station/workcell allowed device types and intended operations. | Correct device use. |
| PER-FR-003 | 46 | Barcode scanner | Support keyboard wedge only for noncritical/simple cases; preferred explicit scanner SDK/serial/HID service with source identity. | Source clarity. |
| PER-FR-004 | 46 | Barcode parsing | Versioned barcode parser supports GS1/UDI/custom/internal labels; raw scan retained. | Deterministic parsing. |
| PER-FR-005 | 46 | Scan validation | Server/domain validates scanned business object against expected material/product/lot/serial/location/action. | No trust in text. |
| PER-FR-006 | 46 | Duplicate scan | Debounce/duplicate handling does not suppress legitimate repeated actions; operation context determines idempotency. | Safe UX. |
| PER-FR-007 | 46 | Balance integration | Registered balance delivers value, unit, stable flag, device time/status and calibration identity. | Weighing evidence. |
| PER-FR-008 | 46 | Stable reading | Device/adapter-specific stable criteria must be released/configured; UI cannot accept transient value as stable. | Accuracy. |
| PER-FR-009 | 46 | Balance tare | Tare operation/status captured when workflow requires; software distinguishes gross/tare/net. | Reproducibility. |
| PER-FR-010 | 46 | Manual fallback | Manual weight/result only if workflow policy permits and reason/verifier requirements met. | Controlled fallback. |
| PER-FR-011 | 46 | Label printer | Print request uses exact released template/artwork, variable data and printer identity. | Controlled labeling. |
| PER-FR-012 | 46 | Print acknowledgement | Where printer supports it, capture job/print status; lack of status does not fabricate successful physical application. | Boundary. |
| PER-FR-013 | 46 | Reprint | Reprint is a new controlled print action with reason/counter. | Trace. |
| PER-FR-014 | 46 | Tester integration | Functional/device testers return test ID, unit/serial, method/program version, values, result, raw evidence and tester identity. | eDHR evidence. |
| PER-FR-015 | 46 | Vision system | Capture inspected unit/lot, recipe/model version, defect classification, image/evidence ref and system confidence if used. | Inspection trace. |
| PER-FR-016 | 46 | AI/vision decision | Automated pass/fail only if validated approved model/rule; otherwise advisory result requiring operator/QA decision. | Controlled AI. |
| PER-FR-017 | 46 | File-producing instrument | Import original file/export with checksum and parse result through versioned adapter. | Data integrity. |
| PER-FR-018 | 46 | Peripheral eligibility | Calibration/qualification/maintenance status checked through Equipment module before regulated use. | Valid equipment. |
| PER-FR-019 | 46 | Station lock | Critical workflow binds expected station/peripheral so another nearby device cannot submit without authorization. | Context. |
| PER-FR-020 | 46 | Hot-plug/reconnect | Reconnect preserves device identity and generates session boundary. | Resilience. |
| PER-FR-021 | 46 | Device substitution | Replacement device requires eligibility and station policy; no hidden substitution. | Trace. |
| PER-FR-022 | 46 | Local UI | Operator sees device connected/eligible/stable/source status before action. | Transparency. |
| PER-FR-023 | 46 | Raw input preservation | Raw scan/weight/test payload retained or hashed/evidenced where required. | Auditability. |
| PER-FR-024 | 46 | Security | USB/serial/network device access restricted to gateway service; arbitrary removable-storage use prohibited by deployment hardening. | Security. |
| PER-FR-025 | 46 | Simulation | Peripheral simulators available for CI and validation. | Testability. |
| MAP-FR-001 | 47 | Machine source master | Define machine/PLC/SCADA source identity, equipment link, protocol connector and site/line. | Canonical source. |
| MAP-FR-002 | 47 | Tag/point mapping | Versioned mapping from native tag/node/register/topic to domain parameter/evidence code. | Stable semantics. |
| MAP-FR-003 | 47 | Mapping lifecycle | Draft, engineering test, review, released/effective, superseded/suspended. | Controlled configuration. |
| MAP-FR-004 | 47 | Type validation | Mapping defines native type, expected type, parsing and null/invalid handling. | No implicit casts. |
| MAP-FR-005 | 47 | Engineering units | Raw unit, canonical unit and approved conversion reference. | Reproducible. |
| MAP-FR-006 | 47 | Scale/offset | Scaling defined explicitly; test vectors required. | No hidden conversion. |
| MAP-FR-007 | 47 | Quality mapping | Native quality/status to canonical quality mapping versioned. | Integrity. |
| MAP-FR-008 | 47 | Timestamp semantics | Choose source/server/gateway timestamp usage and freshness thresholds by point. | Time clarity. |
| MAP-FR-009 | 47 | Sampling strategy | Poll/subscription/event-only/deadband/aggregation semantics explicit. | Acquisition behavior. |
| MAP-FR-010 | 47 | Deadband | Engineering deadband may reduce telemetry but cannot suppress events required as regulated evidence. | Completeness. |
| MAP-FR-011 | 47 | Aggregation | High-frequency raw data may aggregate min/max/avg/end/event window only under approved rule, with raw evidence retention policy. | Scalable evidence. |
| MAP-FR-012 | 47 | Batch context binding | Mapping can bind observation to active batch/step/operation by server-issued context token or deterministic line state. | Correct association. |
| MAP-FR-013 | 47 | No heuristic batch assignment | Do not guess batch solely from time proximity when explicit context is required. | Trace. |
| MAP-FR-014 | 47 | Evidence rule | Define which observations become GxP step results, process evidence, alarms, EM events or historian-only telemetry. | Clear data ownership. |
| MAP-FR-015 | 47 | Alarm mapping | Machine alarms mapped to severity/event code and batch/equipment impact rule. | Exception handling. |
| MAP-FR-016 | 47 | State mapping | Machine state/run/idle/fault/changeover may feed execution timeline but does not independently transition GxP batch state unless approved orchestration rule does. | Authority boundary. |
| MAP-FR-017 | 47 | Setpoint vs actual | Store/map setpoint and measured actual separately. | Evidence clarity. |
| MAP-FR-018 | 47 | Command profile | Machine commands defined as allowlisted operation with typed parameters, target, preconditions, authorization, signature, timeout and read-back verification. | Safe commands. |
| MAP-FR-019 | 47 | Command disabled default | No generic tag/register write endpoint exposed to normal UI/API. | Security. |
| MAP-FR-020 | 47 | Local interlock | Command execution requires PLC/machine local safety/interlock; software never bypasses physical control logic. | Safety. |
| MAP-FR-021 | 47 | Command correlation | Command ID links request, approval, machine write, acknowledgement/read-back and resulting evidence. | Trace. |
| MAP-FR-022 | 47 | Command failure | Timeout/readback mismatch produces failure/hold/deviation according to profile, not optimistic success. | Fail safe. |
| MAP-FR-023 | 47 | SCADA integration | Existing SCADA may remain visualization/control system; eBMR consumes approved data/events through Edge. | Brownfield friendly. |
| MAP-FR-024 | 47 | Historian integration | Raw/high-frequency data can be persisted in historian/time-series and referenced by evidence manifest/checksum. | Scale. |
| MAP-FR-025 | 47 | Evidence window | For critical operation, capture pre/during/post time window or cycle dataset reference according to mapping. | Context. |
| MAP-FR-026 | 47 | Cycle/batch summary | Machine cycle produces summary with cycle ID, start/end, parameters, alarms and raw evidence reference. | Sterile/device/process. |
| MAP-FR-027 | 47 | Mapping change impact | Change mapping requires Change Control/validation impact when GxP-relevant; open batches keep issued mapping version. | Validated state. |
| MAP-FR-028 | 47 | Commissioning | Engineering test/simulation path clearly separated from production GxP data. | No test contamination. |
| MAP-FR-029 | 47 | Data replay | Historian/backfill replay tagged and idempotent; cannot silently appear as live data. | Semantics. |
| MAP-FR-030 | 47 | Review-by-exception | Out-of-limit machine data, alarms, gaps, manual fallback and mapping changes visible in QA review. | Quality awareness. |
| MAP-FR-031 | 47 | Export | Inspection export can include machine evidence summary plus source file/reference/hash. | Reproducible. |
| MAP-FR-032 | 47 | Performance | Millions of telemetry points/day do not require millions of Frappe rows; appropriate storage tiers enforced. | Scale. |
