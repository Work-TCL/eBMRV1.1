# WP-07 — Function Contracts

Every function must specify typed inputs, validations, authorization/qualification/SoD, signature requirement, processing rules, DB reads/writes, transaction boundary, outputs, events, errors, idempotency and concurrency. Full rows: `docs/generated/03_FUNCTION_CATALOGUE.csv` filtered by module.

| Function | Doc | Caller | Inputs | Preconditions | Output |
|---|---|---|---|---|---|
| registerERPInstance() | 48 | Platform Admin | tenant_id; site_scope; provider_type; endpoint; auth_ref; capabilities | Admin authorized; secret reference valid; provider installed | ERPInstance |
| getCapabilities() | 48 | Integration Gateway startup | erp_instance_id | Instance active | ERPCapabilities |
| resolveExternalMapping() | 48 | Any integration operation | internal_type; internal_id; external_system; mapping_context | Mapping exists/effective or creation policy allows | ExternalMapping |
| createExternalMapping() | 48 | Controlled sync/admin | internal_id; external_id; entity_type; mapping_source; evidence | Uniqueness and ownership rules satisfied | ExternalMapping |
| queueERPCommand() | 48 | GxP domain after commit | command_type; source_event_id; source_record; canonical_payload | Source GxP transaction committed; capability supported | ERPCommandReceipt |
| dispatchERPCommand() | 48 | Integration worker | integration_command_id | Command pending/retry-due; adapter healthy | ERPCommandOutcome |
| ingestERPEvent() | 48 | Webhook/poller/import | instance_id; external_event_id; payload; source_version | Authenticated source; schema known | ERPInboundEventReceipt |
| reconcileERPObject() | 48 | Scheduled/admin | reconciliation_scope; internal_ref; external_ref | Mapping available | ERPReconciliationResult |
| retryERPCommand() | 48 | Integration Admin/worker | command_id; reason/manual flag | Command failed/retryable; payload unchanged | RetryReceipt |
| cancelPendingERPCommand() | 48 | Integration Admin/domain supersession | command_id; reason | Command not externally committed; cancellation authorized | CancelReceipt |
| authenticateERPNext() | 49 | Adapter startup | base_url; credential_ref | Credential secret resolves; TLS valid | ERPNextSessionInfo |
| getItem() | 49 | Provider caller | external item code | Authenticated; read permission | ERPItem |
| getPurchaseOrder() | 49 | Procurement sync | PO name | Read permission | ERPPurchaseOrder |
| createPurchaseOrder() | 49 | Procurement service | canonical PurchaseOrderCommand | Provider capability enabled; mappings/UOM/supplier valid | ExternalTransactionRef |
| postGoodsReceipt() | 49 | Material Receipt service | GoodsReceiptCommand | GxP receipt committed; PO/item/warehouse mappings valid | ExternalTransactionRef |
| postInventoryIssue() | 49 | Consumption service | InventoryIssueCommand | GxP consumption committed; stock-entry mapping valid | ExternalTransactionRef |
| postInventoryReturn() | 49 | Material Return service | InventoryReturnCommand | GxP return committed | ExternalTransactionRef |
| getInventoryBalance() | 49 | Reconciliation | item/warehouse/batch query | Read permission; mapping valid | ERPInventoryBalance[] |
| getWorkOrder() | 49 | Batch planning/import | work_order_name | Read permission | ERPProductionOrder |
| healthCheck() | 49 | Scheduler/admin | instance_id | Credentials available | ERPHealth |
| getSAPProduct() | 50 | Master sync | sap_material_id | SAP product API configured/authenticated | ERPItem |
| getSAPInventoryBalance() | 50 | Reconciliation | plant; storage_location; material; batch? | Inventory API configured | ERPInventoryBalance[] |
| postSAPMaterialDocument() | 50 | Outbound inventory worker | canonical material movement command | Movement mapping/plant/location/material/UOM valid; source GxP tx committed | ExternalTransactionRef |
| reverseSAPMaterialDocument() | 50 | Authorized correction integration | original external ref; reversal reason; source GxP correction/ref | GxP correction transaction exists; reversal mapping allowed | ExternalTransactionRef |
| getSAPProductionOrder() | 50 | Batch import/planning | production_order_id | API/profile supports query | ERPProductionOrder |
| fetchCSRFSecurityContext() | 50 | SAP client | service endpoint | Auth valid | SAPSecurityContext |
| mapSAPBusinessError() | 50 | SAP client | HTTP status; OData/business message payload | Raw response available | IntegrationError |
| reconcileSAPMaterialDocument() | 50 | Reconciliation job | command_id; external material doc ref | External ref known or lookup window bounded | ReconciliationResult |
| postOracleInventoryTransaction() | 51 | Integration worker | InventoryCommand; oracle_instance | Oracle API profile/privileges/mappings valid | ExternalTransactionRef |
| postOracleReceipt() | 51 | Material Receipt integration | GoodsReceiptCommand | Oracle receiving profile configured | ExternalTransactionRef |
| getOracleInventory() | 51 | Reconciliation | org/item/subinventory/lot query | Read privilege | ERPInventoryBalance[] |
| queryDynamicsEntity() | 51 | Master/reconciliation | entity_name; company; filter; select | Entity allowlisted; auth/company valid | Canonical DTO[] |
| postDynamicsEntity() | 51 | Integration worker | entity_name; company; canonical command | Write-capable entity/service approved; mapping valid | ExternalTransactionRef |
| submitDynamicsDataPackage() | 51 | Bulk sync worker | package_manifest; file/evidence ref | Bulk pattern enabled; package schema released | ExternalJobRef |
| callCustomREST() | 51 | Generic adapter | operation_id; canonical request | OpenAPI operation allowlisted; auth/mapping valid | Canonical/ExternalTransactionRef |
| exchangeCustomFile() | 51 | Batch scheduler | file_contract_id; canonical records | SFTP/file profile active; schema/version known | ExternalBatchRef |
| reconcileCustomWrite() | 51 | Reconciliation | command_id; provider-specific lookup keys | Adapter has required readback implementation | ReconciliationResult |
| stageInboundMasterRecords() | 52 | ERP poll/webhook/bulk import | entity_type; raw records; source cursor; instance | Source authenticated/schema recognized | StagingBatchReceipt |
| normalizeMasterRecord() | 52 | Sync processor | staging_record; mapping_profile_version | Profile effective | NormalizedExternalMaster |
| matchInternalEntity() | 52 | Sync processor/admin | normalized external master; entity type | Matching policy available | MasterMatchResult |
| proposeMapping() | 52 | Sync processor/admin | external_ref; internal_ref; evidence; confidence | No active conflicting mapping | MappingProposal |
| approveMapping() | 52 | Data Owner/QA if required | mapping_id; expected_version; signature if policy | Reviewer authorized; identity/UOM/site validations pass | ActiveMapping |
| applyERPProjectionUpdate() | 52 | Sync processor | normalized record; active mapping | Field ownership matrix loaded | ProjectionUpdateResult |
| raiseMasterConflict() | 52 | Sync processor | entity/mapping; field diffs; source versions | Conflict material | MasterConflict |
| resolveMasterConflict() | 52 | Data Owner | conflict_id; resolution; reason; approvals | Authorized; source/current versions unchanged | ConflictResolution |
| advanceSyncCheckpoint() | 52 | Sync worker | instance/entity; cursor/watermark; batch_id | All staging records durably stored | SyncCheckpoint |
| reconcileMasterMappings() | 52 | Scheduled/admin | instance; entity_type; scope | Provider available | MasterReconciliationReport |
| classifyIntegrationError() | 53 | Adapter/client | provider response/exception; operation profile | Raw diagnostic captured | CanonicalIntegrationError |
| computeRetryDecision() | 53 | Worker | command; canonical error; retry policy; attempt history | Error classified | RetryDecision |
| scheduleRetry() | 53 | Worker | command_id; RetryDecision | Retry allowed and attempts remain | RetrySchedule |
| markDeadLetter() | 53 | Worker | command_id; terminal error | No safe automatic retry | DeadLetterReceipt |
| ensureIdempotency() | 53 | Outbound handler | idempotency_key; payload_hash; source_event | Key format valid | IdempotencyDecision |
| dedupeInboundEvent() | 53 | Inbound handler | erp_instance_id; external_event_id; payload_hash | Authenticated source | InboundDedupeDecision |
| reconcileUncertainCommit() | 53 | Worker | command_id; provider lookup strategy | Command in TIMEOUT_UNCERTAIN or equivalent | UncertainCommitResolution |
| createReconciliationRun() | 53 | Scheduler/Admin | instance; reconciliation_type/scope; cutoff | Provider available | ReconciliationRun |
| recordReconciliationDifference() | 53 | Reconciliation processor | run_id; difference type; internal/external evidence | Difference material | ReconciliationDifference |
| resolveReconciliationDifference() | 53 | Integration/Data Owner | difference_id; resolution; reason; correction refs | Authorized; versions current | ResolutionReceipt |
| tripCircuitBreaker() | 53 | Worker policy | instance/operation; failure window | Threshold exceeded | CircuitBreakerState |
| closeCircuitBreaker() | 53 | Health probe | instance/operation | Successful probes/half-open policy | CircuitBreakerState |
