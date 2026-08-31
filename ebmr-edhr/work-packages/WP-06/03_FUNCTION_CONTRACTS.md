# WP-06 — Function Contracts

Every function must specify typed inputs, validations, authorization/qualification/SoD, signature requirement, processing rules, DB reads/writes, transaction boundary, outputs, events, errors, idempotency and concurrency. Full rows: `docs/generated/03_FUNCTION_CATALOGUE.csv` filtered by module.

| Function | Doc | Caller | Inputs | Preconditions | Output |
|---|---|---|---|---|---|
| enrollGateway() | 43 | Installer / Site Admin | bootstrap_token:string; site_id:uuid; gateway_fingerprint:string; csr:PEM | Token valid, unused, scoped to site; fingerprint not already active | GatewayEnrollmentResult{gateway_id,cert_chain,config_endpoint,expires_at} |
| loadRuntimeConfig() | 43 | Gateway startup / config refresh | config_version?:string | Gateway identity valid; signed config available | ValidatedGatewayConfig |
| activateRuntimeConfig() | 43 | Config manager | validated_config | No running transaction using incompatible mapping; rollback point available | ActivationResult{active_version,restarted_connectors} |
| startConnector() | 43 | Supervisor | connector_id; connector_config_version | Plugin installed; secrets resolved; endpoint config valid | ConnectorHandle/status |
| stopConnector() | 43 | Supervisor/Admin | connector_id; reason | Authorized operational action | StopResult |
| ingestSourceObservation() | 43 | Protocol plugin | RawSourceObservation | Connector active; source mapping exists or configured quarantine path | EdgeObservationEnvelope |
| normalizeObservation() | 43 | Ingestion pipeline | raw_value:any; source_type; mapping_version | Mapping version effective; type/UOM mapping valid | NormalizedObservation |
| appendDeliveryEnvelope() | 43 | Ingestion pipeline | EdgeObservationEnvelope | Local buffer writable; event_id unique | BufferedEnvelopeRef{event_id,seq} |
| forwardPendingBatch() | 43 | Forwarder timer / connectivity restored | max_items:int; max_bytes:int | Upstream authenticated; no active backoff | ForwardResult{sent_event_ids,server_ack} |
| applyServerAck() | 43 | Forwarder | ack ranges/event IDs | Ack signed/authenticated and scoped to gateway | AckResult |
| reportHealth() | 43 | Periodic timer | runtime metrics/connectors/storage/clock/certs | Gateway identity valid | HealthAck |
| evaluateClockHealth() | 43 | Periodic timer | system_time; ntp_status; source | Clock policy loaded | ClockHealth{offset_ms,status} |
| rotateGatewayCertificate() | 43 | Scheduled/Admin | gateway_id; CSR | Current identity valid; rotation authorized; expiry window/policy | CertificateRotationResult |
| installSignedUpdate() | 43 | Controlled deployment | artifact_ref; signature; expected_version; change_id | Approved release/change; artifact signature valid | UpdateResult{old,new,status} |
| quarantineConnector() | 43 | Security/health rule | connector_id; reason; evidence | Authorized rule/admin | QuarantineResult |
| submitMachineCommand() | 43 | GxP Integration Gateway only | approved_command_profile; target; parameters; command_id | Feature enabled; command allowlisted; actor/policy/signature/local interlock valid | CommandExecutionReceipt |
| connect() | 44 | Edge supervisor | ConnectorConfig | Config valid; credentials available | ConnectionResult{session_id,capabilities} |
| disconnect() | 44 | Supervisor / shutdown | session_id; reason | Session exists | void/DisconnectResult |
| readOnce() | 44 | Commissioning or polling scheduler | SourceAddress; read_options | Connected; read rate allowed | RawSourceObservation |
| subscribe() | 44 | Subscription scheduler | SourceAddress[]; sampling/publishing config | Protocol supports subscription; connected | SubscriptionHandle |
| unsubscribe() | 44 | Config change/shutdown | subscription_id | Subscription exists | void |
| browse() | 44 | Engineering mapping UI | root/node; filters; continuation | Engineering permission; non-production or approved commissioning mode | BrowseResult[] |
| write() | 44 | Approved machine command only | SourceAddress; typed value; command context | Driver writable + runtime command policy + interlock authorized | DriverWriteReceipt |
| healthCheck() | 44 | Periodic supervisor | session_id | Driver instantiated | DriverHealth |
| decodePayload() | 44 | MQTT/custom message callback | bytes; decoder_version; content_type | Decoder released for source | DecodedFields |
| mapNativeQuality() | 44 | Driver read/subscription | native status/error | Mapping table released | CanonicalQuality |
| reconnect() | 44 | Supervisor after disconnect | connector_id; previous state | Backoff elapsed | ReconnectResult |
| testMapping() | 44 | Engineering UI | mapping draft; one-shot source request | Authorized engineer; no production commit | MappingPreview |
| appendEnvelope() | 45 | Edge ingestion | envelope | event_id unique; storage healthy | BufferedEnvelopeRef |
| selectForwardBatch() | 45 | Forwarder | max_count; max_bytes; now | No current send lock or safe concurrent selector | ForwardBatch |
| sendBatch() | 45 | Forwarder | ForwardBatch | Upstream auth and network available | ServerBatchAck |
| applyAck() | 45 | Forwarder | ServerBatchAck | Ack gateway ID valid; event IDs exist | AckApplyResult |
| recoverInFlight() | 45 | Startup | recovery_cutoff | DB integrity valid | RecoveryResult |
| computeDiskPressure() | 45 | Health timer | filesystem stats; policy thresholds | Policy loaded | DiskPressureStatus |
| purgeAcked() | 45 | Retention job | retention_cutoff; max_rows | Only ACKED/PURGE_ELIGIBLE | PurgeResult |
| verifyBufferIntegrity() | 45 | Scheduled/support | range/time window | Storage readable | IntegrityReport |
| replayRejected() | 45 | Integration Admin | event_id; reason; approved mapping/config context | Authorized; exact payload retained | ReplayReceipt |
| storeEvidenceFile() | 45 | Instrument/file adapter | bytes/stream; metadata | Disk capacity; MIME/size policy | EvidenceRef{sha256,path,size} |
| captureBarcodeScan() | 46 | Scanner adapter | raw_scan; scanner_id; station_id; timestamp | Scanner registered/eligible; station active | ScanObservation{raw,parsed,parser_version} |
| validateScanForAction() | 46 | UI/domain action | ScanObservation; expected_entity_type; action_context | User/action authorized; expected requirement exists | ScanValidationResult |
| readStableWeight() | 46 | Dispensing UI | balance_id; timeout_ms; expected_uom | Balance eligible; driver connected | StableWeightReading |
| recordTare() | 46 | Dispensing workflow | balance_id; tare_context | Tare allowed; container context known | TareReceipt |
| submitManualWeight() | 46 | Operator UI | value; uom; reason; verifier/signature if required | Fallback policy allows; actor qualified | ManualWeightResult |
| createPrintJob() | 46 | Packaging/dispensing module | template_version; variable_data; printer_id; copies | Template released; printer eligible; action authorized | PrintJobReceipt |
| reprintLabel() | 46 | Authorized UI | original_print_job_id; reason | Reprint policy/role valid | PrintJobReceipt |
| ingestTesterResult() | 46 | Tester adapter | tester payload; tester_id; program_version; unit/serial | Tester eligible; mapping released | CanonicalTesterResult |
| ingestVisionResult() | 46 | Vision adapter | inspection payload; model/recipe version; image refs | System eligible; model/version approved for intended use | VisionInspectionResult |
| registerPeripheralSession() | 46 | Gateway runtime | device_id; station_id; connection metadata | Device registered; station mapping valid | PeripheralSession |
| releaseSignalMapping() | 47 | Integration Engineer + QA/Validation | mapping_draft_id; signatures | Mapping tested; test vectors pass; change/validation approvals complete | ReleasedSignalMapping |
| resolveBatchContext() | 47 | Integration Gateway | gateway/device/line; context token or active-operation reference; observation | Context binding policy configured | BatchContext\ |
| evaluateEvidenceRouting() | 47 | Integration Gateway | observation; released mapping | Mapping effective; quality/time known | EvidenceRouteDecision |
| createStepResultCandidate() | 47 | Integration Gateway | observation; batch/step context; parameter mapping | Batch step expects parameter; source allowed; freshness/quality acceptable | GxPCommandEnvelope |
| createMachineAlarmEvent() | 47 | Integration Gateway | alarm observation; mapping | Alarm code mapping exists | AlarmEventCommand |
| buildCycleEvidenceManifest() | 47 | Cycle aggregator | cycle_id; observation/event refs; start/end; profile | Cycle complete or checkpoint; evidence refs available | CycleEvidenceManifest |
| submitApprovedMachineCommand() | 47 | GxP service | command_profile_id; target; typed params; actor/signature/context | Command profile effective; policy+SoD+signature; batch/equipment state valid | CommandRequestReceipt |
| executeMachineCommandAtEdge() | 47 | Edge command handler | command_id; signed request; target; params | Gateway/site/expiry/signature valid; local allowlist/interlock; connector writable | EdgeCommandReceipt |
| finalizeMachineCommand() | 47 | GxP Integration service | EdgeCommandReceipt | Matches pending command; not expired; readback rules satisfied | MachineCommandOutcome |
| replayHistoricalEvidence() | 47 | Integration Admin | evidence IDs/time range; reason; target mapping mode | Authorized; historical source retained | ReplayJobReceipt |
