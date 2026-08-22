# WP-07 — Scope & Requirements

**In scope:** Documents 48, 49, 50, 51, 52, 53

## Document 48 — Enterprise ERP Integration Architecture & Provider Contract (SPEC-ERP-001)

- Code location: `services/integration-gateway`
- Authoritative store: External ERP (commercial truth) / PostgreSQL (GxP truth) per Doc 48 ownership matrix
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: ERP-ARC-001..030 (30)

## Document 49 — ERPNext Adapter Detailed Contract (SPEC-ERP-002)

- Code location: `services/integration-gateway`
- Authoritative store: External ERP (commercial truth) / PostgreSQL (GxP truth) per Doc 48 ownership matrix
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: ENXT-FR-001..024 (24)

## Document 50 — SAP S/4HANA Adapter Contract (SPEC-ERP-003)

- Code location: `services/integration-gateway`
- Authoritative store: External ERP (commercial truth) / PostgreSQL (GxP truth) per Doc 48 ownership matrix
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: SAP-FR-001..025 (25)

## Document 51 — Oracle Fusion, Dynamics 365 & Custom ERP Adapter Contracts (SPEC-ERP-004)

- Code location: `services/integration-gateway`
- Authoritative store: External ERP (commercial truth) / PostgreSQL (GxP truth) per Doc 48 ownership matrix
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: MULTI-FR-001..024 (24)

## Document 52 — Master Data Synchronization, Mapping & Reconciliation (SPEC-ERP-005)

- Code location: `services/integration-gateway`
- Authoritative store: External ERP (commercial truth) / PostgreSQL (GxP truth) per Doc 48 ownership matrix
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: MDS-FR-001..028 (28)

## Document 53 — Integration Error Handling, Retry, Idempotency & Reconciliation (SPEC-ERP-006)

- Code location: `services/integration-gateway`
- Authoritative store: External ERP (commercial truth) / PostgreSQL (GxP truth) per Doc 48 ownership matrix
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: INT-FR-001..030 (30)

## All requirements

| ID | Doc | Requirement | Behaviour | Acceptance |
|---|---|---|---|---|
| ERP-ARC-001 | 48 | Provider abstraction | Expose ERPProvider contracts for master data, procurement, inventory, manufacturing references and distribution references without vendor types in GxP domain. | Vendor-neutral core. |
| ERP-ARC-002 | 48 | Instance registry | Register ERP instance, tenant/site scope, vendor/type, environment, auth method, endpoint/version and enabled capabilities. | Multi-customer deployment. |
| ERP-ARC-003 | 48 | Capability discovery | Adapter declares supported operations rather than GxP assuming all ERP functions exist. | Safe compatibility. |
| ERP-ARC-004 | 48 | Ownership matrix | Every shared business object/field has one authoritative owner and defined projection/mapping owner. | No dual-master ambiguity. |
| ERP-ARC-005 | 48 | External mappings | Maintain internal immutable ID ↔ external ERP ID mapping with mapping version/status/source. | Stable identity. |
| ERP-ARC-006 | 48 | Material/item sync | ERP item/material data may seed commercial projection; regulated material/spec identity remains GxP-controlled. | Correct ownership. |
| ERP-ARC-007 | 48 | Supplier sync | ERP supplier can map to GxP supplier identity but does not imply approved-supplier status. | Quality boundary. |
| ERP-ARC-008 | 48 | PO reference | GxP may create/read/revise regulated procurement reference through provider while pricing/terms remain ERP-owned where applicable. | Procurement integration. |
| ERP-ARC-009 | 48 | Goods receipt posting | GxP receipt may trigger ERP goods receipt after authoritative GxP receipt commit. | Physical/commercial alignment. |
| ERP-ARC-010 | 48 | Quality status posting | GxP material release/reject may map to ERP stock/status representation, but ERP cannot create GxP release. | One-way authority. |
| ERP-ARC-011 | 48 | Reservation posting | Batch reservation may create ERP reservation/reference if integration profile requires. | Planning sync. |
| ERP-ARC-012 | 48 | Consumption posting | Material consumption posts to ERP after GxP consumption commit with exact transaction reference/idempotency. | No duplicate issue. |
| ERP-ARC-013 | 48 | Return posting | Material return posts separately with source GxP transaction reference. | Trace. |
| ERP-ARC-014 | 48 | Scrap/destruction posting | Approved GxP scrap/destruction triggers ERP quantity posting without altering GxP disposition. | Boundary. |
| ERP-ARC-015 | 48 | Finished goods receipt | Final produced/packaged quantity can be posted to ERP as unreleased/blocked or released stock according to integration profile. | No premature availability. |
| ERP-ARC-016 | 48 | Release availability | Final QA release event may move ERP stock to available/released state through configured mapping. | Commercial availability. |
| ERP-ARC-017 | 48 | Production order reference | ERP production/manufacturing order may be imported as planning/source reference; eBMR recipe/batch snapshot remains GxP truth. | MES boundary. |
| ERP-ARC-018 | 48 | Warehouse/location mapping | Map sites/warehouses/bins/locations with explicit ownership and allowed direction. | No silent location mismatch. |
| ERP-ARC-019 | 48 | UOM mapping | Controlled internal UOM ↔ ERP UOM mapping; incompatible conversions rejected. | Quantity integrity. |
| ERP-ARC-020 | 48 | Lot/serial mapping | Preserve ERP lot/serial references while internal genealogy remains authoritative. | Traceability. |
| ERP-ARC-021 | 48 | Transaction command ledger | Every outbound ERP command stored with command ID, source GxP event/transaction, payload hash, state and external response/reference. | Reconciliation. |
| ERP-ARC-022 | 48 | Inbound event ledger | Every inbound webhook/poll/import event stored/idempotently processed before projections. | Replay safe. |
| ERP-ARC-023 | 48 | Async default | Use asynchronous outbox/worker pattern for most ERP writes; synchronous dependency reserved for explicitly required pre-action checks. | Resilience. |
| ERP-ARC-024 | 48 | No distributed 2PC | Do not use distributed two-phase commit across GxP and ERP. | Failure isolation. |
| ERP-ARC-025 | 48 | Reconciliation | Scheduled and on-demand reconciliation compares expected vs external state with explicit difference type. | Detect drift. |
| ERP-ARC-026 | 48 | Failure states | Integration failures never fabricate success; physical/GxP transaction remains separately visible with ERP posting pending/failed. | Truth. |
| ERP-ARC-027 | 48 | Manual recovery | Authorized integration admin may retry/remap/reconcile metadata but cannot change regulated transaction content. | Admin boundary. |
| ERP-ARC-028 | 48 | Security | Per-instance credentials, TLS, least privilege, secret manager, outbound restrictions and API throttling. | Secure integration. |
| ERP-ARC-029 | 48 | Observability | Latency, queue age, failures, duplicates, reconciliation mismatches, vendor throttling and auth-expiry visible. | Operable. |
| ERP-ARC-030 | 48 | Version compatibility | Adapter records vendor/API version and contract version used for each exchange when material to investigation. | Reproducible. |
| ENXT-FR-001 | 49 | Supported API | Use supported Frappe/ERPNext REST/RPC APIs; direct ERPNext MariaDB access prohibited. | Upgrade-safe boundary. |
| ENXT-FR-002 | 49 | Authentication | Token/API-key or approved OAuth/session/service identity profile; credentials per instance. | Secure. |
| ENXT-FR-003 | 49 | Item mapping | Map GxP product/material/component IDs to ERPNext Item codes and UOM. | Identity. |
| ENXT-FR-004 | 49 | Supplier mapping | Map supplier but never infer Approved Supplier status from ERPNext Supplier enabled state. | Quality boundary. |
| ENXT-FR-005 | 49 | Warehouse mapping | Map GxP site/warehouse/location to ERPNext Warehouse where integration mode requires. | Inventory sync. |
| ENXT-FR-006 | 49 | Purchase Order | Read/create/update PO through canonical provider when native procurement/ERP mode configured. | Procurement. |
| ENXT-FR-007 | 49 | Purchase Receipt | Post goods receipt after GxP receipt transaction, preserving PO/item/lot refs. | Receipt sync. |
| ENXT-FR-008 | 49 | Stock Entry issue | Post material issue/consumption through Stock Entry or supported ERPNext transaction abstraction. | Inventory posting. |
| ENXT-FR-009 | 49 | Stock return | Post material return/reversal using supported ERPNext transaction path. | Return sync. |
| ENXT-FR-010 | 49 | Batch/serial | Map ERPNext Batch/Serial references without replacing GxP lot/serial identity. | Trace. |
| ENXT-FR-011 | 49 | Finished goods | Post finished quantity/reference according to configured manufacturing/accounting model. | Output sync. |
| ENXT-FR-012 | 49 | Quality status projection | If ERPNext warehouse/status convention represents quarantine/released stock, mapping is one-way from GxP disposition. | No dual master. |
| ENXT-FR-013 | 49 | Production order reference | Read Work Order/Production Plan reference if customer uses ERPNext planning. | Planning source. |
| ENXT-FR-014 | 49 | External doc names | Store ERPNext doctype/name/document version/status as external reference. | Traceability. |
| ENXT-FR-015 | 49 | Submit/cancel semantics | Adapter understands ERPNext draft/submitted/cancelled document lifecycle and maps external result explicitly. | Correct status. |
| ENXT-FR-016 | 49 | Duplicate prevention | GxP command ID persisted in ERPNext integration reference/custom integration field only through controlled integration design, or maintained connector-side if ERP customization avoided. | Idempotency. |
| ENXT-FR-017 | 49 | Customization minimization | Prefer connector-side mappings and public APIs; do not require modifying ERPNext core. | Maintainability. |
| ENXT-FR-018 | 49 | Custom field policy | If external reference custom fields are required in ERPNext, they are installed by versioned connector migration and documented. | Controlled extension. |
| ENXT-FR-019 | 49 | Rate limiting | Bound requests/retries and handle Frappe validation/session errors. | Resilience. |
| ENXT-FR-020 | 49 | Attachment refs | Do not copy regulated evidence into ERPNext unless customer explicitly requires; store references where sufficient. | Boundary. |
| ENXT-FR-021 | 49 | Reconciliation | Compare purchase receipts/stock entries/work orders with integration ledger. | Integrity. |
| ENXT-FR-022 | 49 | Health | Validate API login, required DocTypes/fields, permissions and connector version. | Support. |
| ENXT-FR-023 | 49 | Permission scope | ERPNext integration user has least privileges for exact operations. | Security. |
| ENXT-FR-024 | 49 | No compliance delegation | ERPNext Workflow/DocStatus cannot substitute for GxP signatures/audit/release. | GxP integrity. |
| SAP-FR-001 | 50 | SAP instance profile | Support S/4HANA Cloud Public/Private/On-Prem profiles with configured API capabilities/version. | Deployment flexibility. |
| SAP-FR-002 | 50 | Auth | OAuth2/mTLS/basic only if approved deployment supports; secrets isolated. | Security. |
| SAP-FR-003 | 50 | Product master | Map canonical item/material through supported Product Master APIs such as API_PRODUCT_SRV where applicable. | Master mapping. |
| SAP-FR-004 | 50 | Material stock | Read inventory/stock through supported SAP inventory API/profile. | Reconciliation. |
| SAP-FR-005 | 50 | Material document | Create/retrieve material movement through supported Material Document API/profile. | Inventory posting. |
| SAP-FR-006 | 50 | Goods receipt | Map GxP receipt to correct SAP movement semantics and PO/order refs. | Receipt. |
| SAP-FR-007 | 50 | Goods issue | Map material consumption to approved movement code/type profile. | Consumption. |
| SAP-FR-008 | 50 | Transfer posting | Map GxP transfer when SAP ownership/profile requires. | Warehouse. |
| SAP-FR-009 | 50 | Reversal | Integration reversal is separate SAP transaction; never used to silently erase GxP physical record. | History. |
| SAP-FR-010 | 50 | Movement mapping | Movement codes/types stored as configuration, not hardcoded across customers. | Customer-specific. |
| SAP-FR-011 | 50 | Plant/storage location | Explicit site ↔ SAP plant/storage-location mapping. | Location integrity. |
| SAP-FR-012 | 50 | Material/UOM | Material number/base unit/alternate UOM mapping controlled. | Quantity integrity. |
| SAP-FR-013 | 50 | Batch/serial | SAP batch/serial refs mapped to internal IDs, not authoritative genealogy. | Trace. |
| SAP-FR-014 | 50 | Production order | Read SAP production/process order reference where customer uses SAP planning/manufacturing. | Planning. |
| SAP-FR-015 | 50 | Blocked/released stock | GxP quality release can project to SAP stock/status movement only through configured Quality-approved mapping. | No dual release. |
| SAP-FR-016 | 50 | Posting date | Posting/document dates derived per integration/business policy and retained with actual GxP physical occurrence time. | Chronology. |
| SAP-FR-017 | 50 | External transaction ref | Store SAP material document/year/item or equivalent transaction keys. | Reconciliation. |
| SAP-FR-018 | 50 | OData batch | Adapter may use OData $batch where supported but preserves per-command idempotency/response mapping. | Efficiency. |
| SAP-FR-019 | 50 | Error mapping | Map SAP HTTP/OData/business messages to stable integration errors while retaining raw diagnostic. | Support. |
| SAP-FR-020 | 50 | CSRF/session handling | Handle required SAP OData CSRF/session mechanics in client layer only. | Correct protocol. |
| SAP-FR-021 | 50 | Throttling/retry | Respect API limits and classify retryable vs business errors. | Resilience. |
| SAP-FR-022 | 50 | API version profile | Technical service/entity versions captured in adapter configuration. | Compatibility. |
| SAP-FR-023 | 50 | Custom BAPI/RFC | Custom/private BAPI/RFC integration allowed only through separate customer adapter profile; not assumed common baseline. | Controlled custom. |
| SAP-FR-024 | 50 | Reconciliation | Query material docs/stock by bounded date/object keys and compare expected commands. | Integrity. |
| SAP-FR-025 | 50 | No SAP regulatory authority | SAP material document success does not constitute eBMR step completion/QA release. | Boundary. |
| MULTI-FR-001 | 51 | Adapter families | Provide Oracle Fusion SCM, Dynamics 365 Finance/Supply Chain and Generic Custom ERP implementations behind ERPProvider. | Vendor choice. |
| MULTI-FR-002 | 51 | Oracle REST profile | Use Oracle SCM REST resources for inventory/receiving/shipping/product references as configured. | Supported integration. |
| MULTI-FR-003 | 51 | Oracle inventory transaction | Map GxP inventory movement to Oracle inventory transaction resource/profile. | Inventory. |
| MULTI-FR-004 | 51 | Oracle receipt | Map receipt to supported Oracle receiving transaction/advice/confirmation pattern. | Receipt. |
| MULTI-FR-005 | 51 | Oracle lot/serial | Preserve Oracle lot/serial references while GxP genealogy remains authoritative. | Trace. |
| MULTI-FR-006 | 51 | Oracle privileges | Service account/API privileges minimized to exact resource operations. | Security. |
| MULTI-FR-007 | 51 | Oracle API release | Adapter configuration stores Oracle REST release/profile such as current 26x documentation rather than hardcoding one forever. | Compatibility. |
| MULTI-FR-008 | 51 | Dynamics integration pattern | Choose OData/data entities for synchronous CRUD-sized integration, data-management package REST for bulk/asynchronous, or custom services where justified. | Correct pattern. |
| MULTI-FR-009 | 51 | Dynamics product entity | Use supported product/item data entities/OData profile when synchronizing commercial item master. | Master mapping. |
| MULTI-FR-010 | 51 | Dynamics inventory | Use customer-supported data entities/services for warehouse/inventory transactions and references. | Inventory. |
| MULTI-FR-011 | 51 | Dynamics company/legal entity | Every request/mapping carries correct company/legal-entity context. | Tenant semantics. |
| MULTI-FR-012 | 51 | Dynamics entity versioning | Entity/custom-service names/fields isolated in adapter profile. | Maintainability. |
| MULTI-FR-013 | 51 | Custom REST adapter | Support OpenAPI-described REST endpoints with canonical mapping, auth, timeout, idempotency and reconciliation. | Generic integration. |
| MULTI-FR-014 | 51 | Custom SOAP adapter | Optional SOAP/WSDL adapter through isolated connector when legacy ERP requires it. | Legacy. |
| MULTI-FR-015 | 51 | Custom file adapter | SFTP/CSV/XML/EDI batch exchange allowed only with manifest, checksum, file identity, acknowledgement and replay rules. | Legacy/batch. |
| MULTI-FR-016 | 51 | Custom DB integration | Direct external ERP database read may be supported only read-only under customer-approved adapter; writes to vendor DB prohibited unless vendor-supported integration says otherwise. | Safety. |
| MULTI-FR-017 | 51 | Canonical DTO mapping | Vendor/custom fields map to canonical ERP DTOs; no business domain depends on raw vendor names. | Abstraction. |
| MULTI-FR-018 | 51 | Capabilities | Each adapter declares exact supported operations and limitations. | No false assumptions. |
| MULTI-FR-019 | 51 | External business error | Vendor rejection classified as nonretryable until input/mapping corrected. | Correct retry. |
| MULTI-FR-020 | 51 | Transport failure | Network/5xx/timeout/throttle classified retryable based on provider profile. | Resilience. |
| MULTI-FR-021 | 51 | Idempotency | Use vendor-provided idempotency/correlation if available plus local command ledger. | No duplicates. |
| MULTI-FR-022 | 51 | Reconciliation | Every write-capable custom adapter must implement a read/lookup/reconciliation path; otherwise production write capability is not approved. | Recoverability. |
| MULTI-FR-023 | 51 | Contract tests | Adapter certification requires simulator/sandbox contract suite. | Quality. |
| MULTI-FR-024 | 51 | No unverified connector | Customer custom adapter cannot be enabled for GxP posting without validation/acceptance profile. | Validated state. |
| MDS-FR-001 | 52 | Master-data catalogue | Define synchronized object types: commercial item, regulated product mapping, material item, supplier, site/plant, warehouse/location, UOM, reason/movement code, cost center/project refs as applicable | Controlled scope. |
| MDS-FR-002 | 52 | Field ownership | Every synchronized field explicitly owned by GxP or ERP; BIDIRECTIONAL ownership disallowed for same semantic field unless conflict policy approved. | No conflict. |
| MDS-FR-003 | 52 | Mapping status | UNMAPPED, PROPOSED, ACTIVE, CONFLICT, SUSPENDED, RETIRED. | Explicit. |
| MDS-FR-004 | 52 | Initial sync | Bulk initial import uses staging, validation and reconciliation before activation. | Safe onboarding. |
| MDS-FR-005 | 52 | Incremental sync | Timestamp/change-token/event/poll strategy vendor-specific but canonical processing identical. | Ongoing sync. |
| MDS-FR-006 | 52 | External change detection | ERP-owned field changes update projection; GxP-owned field changes from ERP create conflict, not overwrite. | Ownership. |
| MDS-FR-007 | 52 | GxP change propagation | Approved GxP-owned projection can be sent outward only if provider profile supports it. | Controlled. |
| MDS-FR-008 | 52 | Identity matching | Prefer explicit external IDs; name/fuzzy match only proposes mapping for human review. | No wrong master link. |
| MDS-FR-009 | 52 | Duplicate detection | Detect duplicate external/internal mappings and block activation. | Integrity. |
| MDS-FR-010 | 52 | UOM mapping | UOM equivalency/conversion approved/versioned; unknown UOM quarantines record. | Quantity safety. |
| MDS-FR-011 | 52 | Plant/site mapping | ERP plant/org/company/location context maps exactly to tenant/site. | Isolation. |
| MDS-FR-012 | 52 | Warehouse mapping | Warehouse/bin/subinventory location mapping explicit and effective-dated. | Logistics. |
| MDS-FR-013 | 52 | Supplier mapping | Commercial supplier identity mapping distinct from GxP manufacturer/approved source status. | Quality. |
| MDS-FR-014 | 52 | Product/material mapping | External item maps to exact internal business identity/version policy, never “latest regulated version” dynamically during historical execution. | History. |
| MDS-FR-015 | 52 | Reference-data mapping | Movement type/reason code/status reference values versioned by ERP instance. | Adapter semantics. |
| MDS-FR-016 | 52 | Effective dates | Mappings can be future-effective and historical mappings remain for old transactions. | Reproducibility. |
| MDS-FR-017 | 52 | Suspension | Suspend mapping on discovered mismatch without deleting history. | Containment. |
| MDS-FR-018 | 52 | Conflict queue | Structured differences with owner/source/current/proposed values and resolution action. | Governance. |
| MDS-FR-019 | 52 | Approval | Critical identity/UOM/site mappings require integration/data-owner approval; quality-critical mappings may require QA/validation. | Controlled. |
| MDS-FR-020 | 52 | Bulk approval restriction | High-risk mappings cannot be blanket-approved without review profile. | Safety. |
| MDS-FR-021 | 52 | Mapping hash/version | Every integration transaction records mapping version/hash used. | Investigation. |
| MDS-FR-022 | 52 | Sync checkpoint | Persist external change cursor/watermark per entity/instance. | Restart safe. |
| MDS-FR-023 | 52 | Replay | Reprocess same inbound master event idempotently. | Replay safe. |
| MDS-FR-024 | 52 | Delete semantics | External deletion/deactivation maps to inactive/suspended projection; never physically deletes GxP-linked master history. | History. |
| MDS-FR-025 | 52 | Reconciliation | Scheduled object counts/key fields/active mapping differences. | Detect drift. |
| MDS-FR-026 | 52 | Data quality metrics | Unmapped, conflict, stale, failed sync and duplicate rates visible. | Operability. |
| MDS-FR-027 | 52 | Audit | Mapping create/change/approve/suspend/merge and conflict resolution audited. | Trace. |
| MDS-FR-028 | 52 | Migration | Customer onboarding mapping/import package retained with source checksum and approval. | Provenance. |
| INT-FR-001 | 53 | Canonical integration message | All inbound/outbound exchanges have message/command/event ID, source, target, schema, correlation, causation and payload hash. | Trace. |
| INT-FR-002 | 53 | Error taxonomy | AUTH, CONFIG, VALIDATION, BUSINESS_REJECT, CONFLICT, RATE_LIMIT, TRANSIENT_NETWORK, SERVER_ERROR, TIMEOUT_UNCERTAIN, SCHEMA, SECURITY, MANUAL_REVIEW. | Consistent handling. |
| INT-FR-003 | 53 | Retry classification | Only retryable categories retry automatically; business/validation/config errors require correction/review. | No retry storms. |
| INT-FR-004 | 53 | Exponential backoff | Configurable capped backoff + jitter; vendor Retry-After honored where applicable. | Resilience. |
| INT-FR-005 | 53 | Maximum attempts | Retry count/time window configurable; exhausted commands enter manual-review/dead-letter. | Bounded. |
| INT-FR-006 | 53 | Idempotency key | Every write command has stable idempotency key derived from immutable source event/operation semantics. | No duplicates. |
| INT-FR-007 | 53 | Payload hash | Same idempotency key with different payload hash is conflict/integrity incident. | Tamper/drift detection. |
| INT-FR-008 | 53 | Uncertain timeout | Timeout after external request may represent committed external transaction; reconcile before replaying create where duplicate risk exists. | Exactly-once effect strategy. |
| INT-FR-009 | 53 | External correlation | Store vendor request/job/doc/reference IDs on every successful/uncertain attempt. | Investigability. |
| INT-FR-010 | 53 | Inbound dedupe | Unique external event/message ID + source instance and payload hash. | Replay safe. |
| INT-FR-011 | 53 | Out-of-order events | Process version/sequence-aware; stale events cannot overwrite newer projection. | Ordering. |
| INT-FR-012 | 53 | Dead letter | Retain failed original payload hash/reference, attempts/errors and required next action. | No loss. |
| INT-FR-013 | 53 | Manual replay | Authorized replay uses exact original payload unless a new corrected command is explicitly created. | Integrity. |
| INT-FR-014 | 53 | Corrected command | Business correction creates new command ID linked to original; never mutate original command payload. | History. |
| INT-FR-015 | 53 | Cancellation | Pending command may be cancelled/superseded only before confirmed external commit and with reason. | State clarity. |
| INT-FR-016 | 53 | Compensation | External reversal/compensation is a new integration command tied to authorized GxP correction/disposition. | No hidden rollback. |
| INT-FR-017 | 53 | Reconciliation types | MISSING_EXTERNAL, EXTRA_EXTERNAL, VALUE_MISMATCH, STATUS_MISMATCH, REFERENCE_MISMATCH, DUPLICATE_EXTERNAL, STALE_MAPPING. | Structured drift. |
| INT-FR-018 | 53 | Reconciliation snapshot | Report records source cutoff, query keys, external response refs and mapping versions. | Reproducible. |
| INT-FR-019 | 53 | Auto-resolve | Only benign known differences/duplicates may auto-resolve under released rule; quantity/status mismatches require review. | Safe. |
| INT-FR-020 | 53 | Integration hold | Critical unresolved integration mismatch can create operational/QA review flag according to module policy. | Risk. |
| INT-FR-021 | 53 | SLA/aging | Track oldest pending, retry age, dead-letter age and reconciliation age. | Operations. |
| INT-FR-022 | 53 | Circuit breaker | Per-instance breaker protects repeated transient vendor failures without losing queued commands. | Stability. |
| INT-FR-023 | 53 | Bulk jobs | Bulk import/export job tracks record-level successes/failures and supports idempotent resume. | Scale. |
| INT-FR-024 | 53 | Rate limiting | Per provider/operation quotas configured. | Vendor-safe. |
| INT-FR-025 | 53 | Security event | Unexpected payload hash/idempotency conflict/source identity mismatch raises security/data-integrity event. | Detection. |
| INT-FR-026 | 53 | Observability | Metrics/logs/traces include correlation IDs but redact sensitive credentials/content. | Support. |
| INT-FR-027 | 53 | Audit | Manual retry/remap/cancel/reconcile resolution audited. | Accountability. |
| INT-FR-028 | 53 | Retention | Integration ledgers retained long enough to support regulated-record investigation and external reconciliation. | Evidence. |
| INT-FR-029 | 53 | Chaos testing | Simulate network partitions, lost responses, duplicates, throttling, partial bulk failure and provider outage. | Reliability. |
| INT-FR-030 | 53 | No silent success | UI never displays external posting successful until Integration Gateway has confirmed/reconciled it. | Truth. |
