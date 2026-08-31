# Claude Code prompt — WP-09 / Document 58: Postmarket Surveillance, Safety Case & Signal Management

TASK:
Implement the Postmarket Surveillance, Safety Case & Signal Management module (SPEC-PM-001) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_58_Postmarket_Surveillance_Safety_Case_Signal_Management_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: PMS-FR-001..034 (34)
- Approved baselines: Document 106 (signature policy), 107 (SoD), 108 (retention), 109 (SLO/RPO),
  110 (precision/UOM), 111 (risk class), 112 (schemas/migrations), 113 (contracts), 114 (glossary)
- Phase-0 artefacts: `docs/generated/03_FUNCTION_CATALOGUE.csv`, `04_DATA_MODEL_CATALOGUE.md`,
  `05_DATABASE_OWNERSHIP_MATRIX.md`, `06_API_CATALOGUE.yaml`, `07_EVENT_CATALOGUE.yaml`,
  `14_ERROR_CODE_REGISTRY.md`, `28_INTENDED_USE_GXP_RISK_MATRIX.md`

RISK CLASS: **HIGHER-PROCESS-RISK** → scripted tests, independent review, mandatory negative and failure evidence

ARCHITECTURE CONSTRAINTS:
- Frappe is UI/configuration only; no core fork or edit.
- PostgreSQL is authoritative for regulated state; MariaDB holds read-only projections.
- Every regulated write goes through the Mutation Gateway → one PostgreSQL transaction carrying
  domain state + record version + audit event + outbox event.
- Signatures follow Document 04 + the approved Document 106 policy; login/MFA is never a signature.
- Audit, vault and evidence history is append-only and superseding.
- Outbox is the authoritative event source; NATS is transport; Temporal is orchestration only.
- Caches, projections, search and reports are rebuildable and never a regulated decision source.
- Adapters and edge never write GxP tables; they submit integration commands.
- AI is advisory; it cannot sign, release, disposition, approve, alter audit or submit reports.

PRECONDITIONS:
- WP-00 foundations exist (contracts tooling, guardrails, CI gates).
- WP-01 GxP Core is available (mutation, policy, signature, audit, vault, rules).
- Contracts for this module are committed before implementation (Document 113).

ALLOWED SCOPE:
- `services/gxp-api/src/modules/postmarket` and its tests
- `contracts/` entries owned by this module
- migrations for entities owned by this module
- Frappe UI surfaces for this module in `apps/ebmr_frappe/`

DO NOT:
- Do not modify anything under `specs/`.
- Do not implement a signature requirement not present in the approved Document 106 policy set
  (emit a policy row and reference the gap instead).
- Do not create a second authoritative store for an entity owned elsewhere.
- Do not add an endpoint to a module whose exposure boundary is "no independent API" (Document 113 §6).
- Do not write a migration for an entity absent from `docs/generated/04_DATA_MODEL_CATALOGUE.md`.
- Do not use binary floating point for a regulated quantity.
- Do not fabricate a test run, scan result or qualification record.
- Do not start work in another work package.

FILES TO CREATE/MODIFY:
```text
services/gxp-api/src/modules/postmarket/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/postmarket/migrations/     # owned entities only
services/gxp-api/src/modules/postmarket/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-pm-001.yaml
contracts/events/spec-pm-001/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-pm-001/
```

REQUIREMENTS TO IMPLEMENT (34):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| PMS-FR-001 | Source registry | Register complaint, service, repair, literature, regulator, distributor, field action, manufacturing, QC, study and external-safety sources with source owner and ingestion profile. | All safety information attributable. |
| PMS-FR-002 | Linked safety case | Create safety_case as a regulatory/surveillance layer referencing the source QMS/service record and version; do not copy source record into a second editable truth. | No duplicated QMS master. |
| PMS-FR-003 | Receipt/awareness chronology | Store source receipt, company initial receipt, regulatory-clock candidate, follow-up receipt and system ingestion timestamps separately. | Deadline reconstruction. |
| PMS-FR-004 | Product resolution | Resolve exact marketed product/application, lot/batch/serial, UDI/NDC and DDCP constituent architecture when known. | Correct regime and genealogy. |
| PMS-FR-005 | Unknown identity queue | Unknown product/lot/serial remains open data-quality task and is never discarded. | Completeness. |
| PMS-FR-006 | Controlled coding | Use versioned event, failure, complaint, device-problem and clinical coding dictionaries; retain code-system/version. | Consistent trending. |
| PMS-FR-007 | Seriousness attributes | Capture death, life-threatening, hospitalization, disability, congenital anomaly and medically-important inputs without automatically deciding reportability. | Safety assessment. |
| PMS-FR-008 | Device-event attributes | Capture death/serious-injury/malfunction candidates, caused/contributed evidence and remedial-action context. | MDR inputs. |
| PMS-FR-009 | Drug/biologic attributes | Capture adverse experience, seriousness, expectedness-reference, causality/reasonable-possibility inputs and reporter/source. | Drug/biologic inputs. |
| PMS-FR-010 | Manufacturing-event surveillance | Allow quality/manufacturing events to enter surveillance even without an injury when profile/rules make them relevant. | Combination-product breadth. |
| PMS-FR-011 | Field-action link | Document 36 field action creates a linked surveillance/regulatory source without duplicating execution data. | Postmarket/QMS connection. |
| PMS-FR-012 | Constituent attribution | Classify possible Drug, Biologic, Device, Interface, Packaging/Label, User Interaction or Unknown involvement. | DDCP analysis. |
| PMS-FR-013 | Multiple assessment tracks | One safety case can feed several independent reportability tracks while remaining one source case. | Combination-product support. |
| PMS-FR-014 | Duplicate detection | Detect probable duplicate reports using source/event/product/patient/device identifiers; original source records are retained. | No lost intake. |
| PMS-FR-015 | Duplicate linking | Link duplicates/related cases to a canonical case without destructive merge. | Integrity. |
| PMS-FR-016 | Follow-up versioning | Every material follow-up creates immutable follow-up version, receipt date, source/evidence and reassessment flags. | Dynamic case. |
| PMS-FR-017 | Expectedness reference | Expectedness assessment references exact labeling/reference-safety-information version used. | Reproducible decision. |
| PMS-FR-018 | Trend population | Define product/family/site/lot/device/constituent/event population and time window. | Meaningful metrics. |
| PMS-FR-019 | Exposure denominator | Use distribution/exposure data with source cutoff/version where available; explicitly mark denominator uncertainty. | Normalized rates. |
| PMS-FR-020 | Signal rules | Versioned statistical/business rules may flag severity/frequency shifts, clusters, recurrence or lot concentration. | Early detection. |
| PMS-FR-021 | Formal safety signal | Open signal from rule or authorized reviewer with frozen case/evidence snapshot. | Controlled signal. |
| PMS-FR-022 | Signal assessment | Assess clinical, device, drug, manufacturing, quality and genealogy evidence, plausibility, scope and action need. | Multidisciplinary review. |
| PMS-FR-023 | Signal state machine | DETECTED→TRIAGE→ASSESSMENT→REFUTED/MONITORING/CONFIRMED→ACTION→CLOSED. | Explicit lifecycle. |
| PMS-FR-024 | Escalation | Confirmed/critical signal may create CAPA, Change, Risk Review, Field Action or Document 59 reportability task. | Actionable. |
| PMS-FR-025 | Genealogy clustering | Use genealogy to identify affected component/material/device lots, equipment routes and process families. | Manufacturing intelligence. |
| PMS-FR-026 | Literature source | Literature event stores citation, source file/reference, reviewer and case/signal relationship. | Broad surveillance. |
| PMS-FR-027 | External authority source | FDA/other authority safety information can be referenced as external evidence without overwriting internal assessment. | Context. |
| PMS-FR-028 | AI advisory boundary | AI may summarize, suggest duplicates/codes/clusters; it cannot decide seriousness, causality, expectedness, reportability or closure. | Human authority. |
| PMS-FR-029 | Privacy | Patient/reporter identifiers use minimum-necessary access, encryption/pseudonymization and explicit retention. | Confidentiality. |
| PMS-FR-030 | Medical review | Where required, qualified medical reviewer records assessment, rationale, evidence and signature/time. | Qualified decision. |
| PMS-FR-031 | Regulatory handoff | Cases requiring formal legal/reporting assessment create one or more Document 59 tracks from a frozen case snapshot. | Deterministic handoff. |
| PMS-FR-032 | Periodic dataset | Qualifying cases/signals/actions are selected into immutable periodic safety dataset by application/reporting profile. | Periodic-report support. |
| PMS-FR-033 | Dashboard | Show serious cases, reportability pending, signal aging, rates, clusters, field actions and follow-up backlog. | Operational visibility. |
| PMS-FR-034 | Audit/export | Complete source→case→follow-up→signal→action history exportable with versions/signatures. | Inspection-ready. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| registerPostmarketSource() | Regulatory Admin | source_type:string; organization:string; channel:string; owner_id:uuid; ingestion_profile_id:uuid | PostmarketSource | PostmarketSourceRegistered; PMS_SOURCE_INVALID; tests duplicate/unauthorized |
| createSafetyCaseLink() | Complaint/Service/Literature ingestion | source_record_type:string; source_record_id:uuid; source_record_version:int; receipt timestamps; product hints | SafetyCase | SafetyCaseCreated; PMS_CASE_DUPLICATE_SOURCE |
| resolveMarketedProduct() | Safety intake processor | case_id:uuid; product identifiers; lot/serial/NDC/UDI | ProductResolution | SafetyProductResolved; PRODUCT_UNRESOLVED |
| classifySafetyCase() | Safety/Regulatory reviewer | case_id; classification DTO; expectedness_ref?; rationale; signature? | SafetyClassification | SafetyCaseClassified; SAFETY_CLASSIFICATION_INCOMPLETE |
| addSafetyCaseFollowup() | Intake/Safety | case_id; new_information; receipt_at; evidence_refs[] | SafetyFollowup | SafetyCaseFollowupReceived |
| findProbableDuplicates() | Processor/AI advisory | case_id; matching_policy_version | DuplicateCandidate[] | SafetyDuplicateCandidatesFound |
| linkDuplicateCases() | Safety reviewer | canonical_case_id; duplicate_case_ids[]; rationale | DuplicateLinkResult | SafetyCasesLinked |
| calculateSurveillanceMetric() | Scheduled analytics | metric_definition_version; scope; period; source_cutoff | SurveillanceMetricSnapshot | PMSMetricCalculated; tests missing denominator/late data |
| evaluateSignalRules() | Scheduled/manual | metric snapshots; case set; signal_rule_versions | SignalRuleResult[] | SafetySignalRuleTriggered |
| openSafetySignal() | Safety reviewer/rule | trigger_refs[]; product/constituent scope; rationale | SafetySignal | SafetySignalOpened |
| assessSafetySignal() | Safety/Medical/Quality team | signal_id; assessment; scope; recommended actions; signatures | SafetySignalAssessment | SafetySignalAssessed |
| escalateSignalToQMSOrRegulatory() | Safety/Regulatory | signal_id; action_type; target_module; rationale | EscalationReceipt | SafetySignalEscalated |
| buildPeriodicSafetyDataset() | Periodic report service | application_id; interval_start; interval_end; report_type; cutoff | PeriodicSafetyDataset | PeriodicSafetyDatasetFrozen |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (4 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `postmarket_source` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `safety_case` | 13 | PostgreSQL (GxP Core, authoritative) |
| `safety_case_followup` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `safety_signal` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (11):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /postmarket/v1/sources` | yes | — |
| `POST /postmarket/v1/safety-cases` | yes | — |
| `POST /postmarket/v1/safety-cases/{id}/resolve-product` | yes | — |
| `POST /postmarket/v1/safety-cases/{id}/classifications` | yes | — |
| `POST /postmarket/v1/safety-cases/{id}/followups` | yes | — |
| `POST /postmarket/v1/safety-cases/{id}/duplicate-links` | yes | — |
| `POST /postmarket/v1/signals` | yes | policy lookup (Doc 106) |
| `POST /postmarket/v1/signals/{id}/assessments` | yes | policy lookup (Doc 106) |
| `POST /postmarket/v1/signals/{id}/escalations` | yes | policy lookup (Doc 106) |
| `POST /postmarket/v1/periodic-datasets:freeze` | yes | — |
| `GET /postmarket/v1/dashboard` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (9):
| Event type | Producer | Dedupe key |
|---|---|---|
| `SafetyCaseCreated` | SPEC-PM-001 | event_id |
| `SafetyProductResolved` | SPEC-PM-001 | event_id |
| `SafetyCaseClassified` | SPEC-PM-001 | event_id |
| `SafetyCaseFollowupReceived` | SPEC-PM-001 | event_id |
| `SafetySignalRuleTriggered` | SPEC-PM-001 | event_id |
| `SafetySignalOpened` | SPEC-PM-001 | event_id |
| `SafetySignalAssessed` | SPEC-PM-001 | event_id |
| `SafetySignalEscalated` | SPEC-PM-001 | event_id |
| `PeriodicSafetyDatasetFrozen` | SPEC-PM-001 | event_id |

UI SURFACES:
- Postmarket Intake Queue
- Safety Case
- Product/Serial/Genealogy Lookup
- Clinical/Device Classification
- Follow-up
- Duplicate Review
- Signal Dashboard
- Signal Assessment
- Trend Explorer
- Action/Handoff
- Periodic Dataset Preview
- Audit/Export

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
Use optimistic concurrency for case/signal versions. Follow-up received during review creates a new version and forces reviewer refresh. Analytics failure cannot close a signal. Missing product identity or denominator is explicit, not inferred.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- complaint already linked
- unknown serial later resolved
- follow-up changes classification
- duplicate source reports linked without deletion
- same-lot cluster
- denominator unavailable
- historical metric formula version remains reproducible
- AI suggestion rejected by reviewer
- signal creates CAPA
- signal creates Field Action
- DDCP case creates multiple reportability tracks
- concurrent follow-up during medical review forces refresh
- privacy role denial
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-09/Document_58_SPEC-PM-001_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-PM-001/<test_case_id>/`.
- A failed case is evidence: never delete it, re-run over it, or edit the expected result to make it pass.
  Raise a defect, record the reference, re-execute as a new dated execution.

TRACEABILITY & STATUS (mandatory at the end of this prompt):
- Update `traceability/TRACEABILITY_MASTER.csv` for every requirement you touched: `build_stage`,
  `verification_state`, `test_case_ids`, `evidence_location`.
- Update `status/build-status.json`: set this module's `stage`, append to `stage_history`, set
  `requirements_state` per requirement, and set `test_pass` / `test_fail` / `test_blocked` from the
  actual recorded results.
- You may only set stages you can evidence, up to and including CODE_COMPLETE and the test states.
  `REVIEWED`, `OQ_EXECUTED`, `QUALIFIED` and `RELEASED` are set by humans, never by you.
- Run `python tooling/status/rollup.py` and include the printed summary in your completion report.

VALIDATION / TRACEABILITY:
- update `docs/generated/15_TEST_TRACEABILITY_MATRIX.csv` and `29_VALIDATION_TRACEABILITY_MASTER.csv`
- state IQ/OQ/PQ impact; HIGHER-PROCESS-RISK functions need retained objective evidence
- Part 11 impact where signatures are involved (Document 88)

ACCEPTANCE CRITERIA:
- every requirement above implemented, traced and tested
- all listed tests executed with real results
- no architecture guardrail violation
- contracts committed before implementation and compatible

SPEC_GAP RULE:
Do not guess regulated behaviour. Append unresolved decisions to `docs/generated/18_SPEC_GAPS.md`
with affected requirements, risk, options and blocking status, then continue only on unaffected work.

BEFORE COMPLETION:
Run lint, typecheck, unit, contract, integration and guardrail checks. Report actual results.

COMPLETION REPORT:
requirements implemented; functions created/changed; files changed; migrations; contract changes;
dependency/licence changes; security impact; **test cases executed with PASS/FAIL/BLOCKED counts and
the case ids of every failure**; validation impact; **traceability and status files updated (include the
rollup summary)**; unresolved SPEC_GAPs; known limitations.
