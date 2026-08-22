# WP-08 — Function Contracts

Every function must specify typed inputs, validations, authorization/qualification/SoD, signature requirement, processing rules, DB reads/writes, transaction boundary, outputs, events, errors, idempotency and concurrency. Full rows: `docs/generated/03_FUNCTION_CATALOGUE.csv` filtered by module.

| Function | Doc | Caller | Inputs | Preconditions | Output |
|---|---|---|---|---|---|
| createInjectableProfileVersion() | 54 | Product/Quality Engineer | product_version_id; subtype; constituent_schema; process_route; control_strategy | Product draft; author authorized; referenced masters exist | InjectableProfileDraft |
| releaseInjectableProfileVersion() | 54 | QA/Regulatory/Validation | profile_id; expected_version; signatures; change_ref | Requirements/risks/validation complete | ReleasedInjectableProfile |
| evaluateInjectableBatchReadiness() | 54 | Batch issue/start | batch_id; profile_version_id; line/equipment context | Issued recipe/profile; materials and equipment available | BatchReadinessResult |
| startFillingStage() | 54 | Operator/Supervisor | batch_id; stage_id; line_id; fill_program_version; bulk_container_ids; e-sign if required | Readiness PASS; active context unique | FillingStageContext |
| recordFillIPCResult() | 54 | QC/IPC/Edge | batch_id; sample_id; actual_value; uom; method/source | Sampling point due; method/spec effective; source allowed | IPCResult |
| recordSyringeUnitOrCount() | 54 | Machine/Edge/Operator | batch_id; count_delta or unit IDs; category filled/reject/sample; source_event | Active filling context; source mapping valid | UnitCountReceipt |
| recordAsepticInterventionForFill() | 54 | Aseptic module | operation_id; intervention_type; actor; start/end; impacted scope | Intervention profile effective | InterventionImpactRef |
| completeFillingStage() | 54 | Supervisor | stage_id; counts; filter refs; IPC completion refs | All mandatory IPC/current filter/EM evidence available; counts reconciled | FillStageCompletion |
| recordPFSFunctionalTest() | 54 | QC/Device Test adapter | sample/unit; test_code; method/program version; values/raw ref | Expected test; tester eligible | PFSFunctionalTestResult |
| evaluatePFSReleaseReadiness() | 54 | QA Release Engine | batch_id; release_profile_version | All required stage evidence materialized | ReleaseReadiness |
| createPFSBatchEvidencePackage() | 54 | QA/Inspector export | batch_id; package_version | Batch state permits export | EvidencePackageRef |
| createInjectorProfileVersion() | 55 | Product/Device Engineer | product_version; injector_type; constituent architecture; assembly/test schemas | Product draft; referenced specs exist | InjectorProfileDraft |
| evaluateInjectorAssemblyReadiness() | 55 | Batch/Work order start | batch_id; line_id; drug_container_lot/unit scope; device component lots | All constituent lots released; line/tools/programs eligible | AssemblyReadiness |
| bindDrugContainerToInjectorUnit() | 55 | Assembly station/Edge | batch_id; drug_container_id; injector_unit_id; scanner evidence | Both identities valid, unused, expected family/status | BindingReceipt |
| recordAssemblyParameter() | 55 | PLC/Tester/Operator | unit/lot; parameter_code; value/uom; source/mapping version | Active assembly operation; expected parameter/source | AssemblyParameterResult |
| executeInjectorFunctionalTest() | 55 | Tester adapter/QC | unit/sample; test_profile; program_version; raw evidence | Tester/program/profile eligible | InjectorFunctionalTestResult |
| evaluateDoseDeliveryResult() | 55 | QC/Rules | raw measurements; calculation rule; acceptance profile | Method/rule released; measurements complete | DoseDeliveryResult |
| recordUnitDisposition() | 55 | QA/Production | unit_id; PASS/REJECT/REWORK; reason; NCR/rework ref | Functional/inspection results current | UnitDisposition |
| completeInjectorAssemblyBatch() | 55 | Supervisor | batch_id; unit counts; rejects; tests; reconciliation | All units/categories resolved; genealogy and counts complete | AssemblyCompletion |
| evaluateInjectorReleaseReadiness() | 55 | QA Release | batch_id/product lot | Constituent and test records current | ReleaseReadiness |
| traceComplaintSerial() | 55 | Complaint/Genealogy | finished_serial | Serial exists | ComplaintTraceGraph |
| createInhalationProfileVersion() | 56 | Product/Quality Engineer | product_version; subtype MDI/DPI; formulation; device constituents; route; tests | Product draft and referenced masters valid | InhalationProfileDraft |
| evaluateInhalationReadiness() | 56 | Batch start | batch_id; formulation/blend lot; device/component lots; environment/equipment | All released/eligible; hold/environment limits valid | InhalationReadiness |
| startInhalerFillRun() | 56 | Production | batch/stage; fill route; equipment/program; target rules | Readiness PASS; route matches profile | FillRunContext |
| recordCrimpOrClosureResult() | 56 | Edge/QC/Operator | unit/sample/lot; crimp dimensions or closure test; source | Expected test/source; equipment eligible | ClosureResult |
| recordInhalerDoseTest() | 56 | QC/LIMS | sample IDs; test code; method; raw results/evidence | Released spec/method; sample chain valid | QCResultSet |
| recordDoseCounterTest() | 56 | Device Tester | unit/sample; program/version; expected count behavior | Device profile requires test; tester eligible | DeviceTestResult |
| completeInhalerManufacturingRun() | 56 | Supervisor | run_id; counts; losses; samples; rejects; mandatory test refs | Counts/IPC/reconciliation complete | RunCompletion |
| evaluateInhalerReleaseReadiness() | 56 | QA Release | batch_id | All required drug/device/QC/package evidence current | ReleaseReadiness |
| traceInhalerLot() | 56 | Genealogy/Complaint | finished lot/unit | Identity exists | GenealogyGraph |
| createCoatedDeviceProfileVersion() | 57 | Product/Quality Engineer | product_version; substrate requirement; drug/coating requirement; coating route; tests; sterilizatio | Product draft; referenced masters valid | CoatedDeviceProfileDraft |
| evaluateCoatingRunReadiness() | 57 | Batch/run start | device substrate lots/units; coating solution lot; equipment; environment; program | Inputs released; hold times valid; equipment/environment eligible | CoatingReadiness |
| startCoatingRun() | 57 | Operator/Supervisor | batch_id; coater_id; program_version; constituent quantities; context | Readiness PASS | CoatingRunContext |
| recordCoatingProcessEvidence() | 57 | Edge/Operator | run_id; parameter_code; value/uom; time; source mapping | Expected mapping/profile; context active | CoatingProcessResult |
| recordDrugLoadingResult() | 57 | QC/Inline measurement | unit/sample/lot; method; raw inputs; calculation rule | Expected sample/test; rule effective | DrugLoadingResult |
| bindDeviceToCoatingConstituent() | 57 | Genealogy service | device lot/serial scope; coating solution/drug lot; run_id | Identities valid and within run scope | GenealogyBinding |
| completeCoatingRun() | 57 | Supervisor | run_id; counts; coating solution usage; losses; sample/reject refs | All process stages/results and dual reconciliation complete | CoatingRunCompletion |
| recordPostSterilizationTest() | 57 | QC/Device Test | finished coated lot/unit; sterilization ref; test profile/results | Required sterilization complete; sample valid | PostSterilizationResult |
| evaluateCoatedDeviceReleaseReadiness() | 57 | QA Release | finished lot/serial scope | Required drug/device/sterilization/QC/QMS evidence complete | ReleaseReadiness |
| traceCoatedDeviceComplaint() | 57 | Complaint/Recall | finished serial/lot | Identity valid | ComplaintTraceGraph |
