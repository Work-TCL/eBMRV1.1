# WP-07 — Traceability Matrix

**Scope:** ERP architecture and adapters, master-data sync, integration error/retry/reconciliation.  
**Requirements:** 161  |  **Test cases:** 427

| Requirement | Module | Risk | Signature | Test cases | Build stage | Verified | Validated |
|---|---|---|---|---|---|---|---|
| ERP-ARC-001 — Provider abstraction | SPEC-ERP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-002 — Instance registry | SPEC-ERP-001 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-003 — Capability discovery | SPEC-ERP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-004 — Ownership matrix | SPEC-ERP-001 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-005 — External mappings | SPEC-ERP-001 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-006 — Material/item sync | SPEC-ERP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-007 — Supplier sync | SPEC-ERP-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-008 — PO reference | SPEC-ERP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-009 — Goods receipt posting | SPEC-ERP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-010 — Quality status posting | SPEC-ERP-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-011 — Reservation posting | SPEC-ERP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-012 — Consumption posting | SPEC-ERP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-013 — Return posting | SPEC-ERP-001 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-014 — Scrap/destruction posting | SPEC-ERP-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-015 — Finished goods receipt | SPEC-ERP-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-016 — Release availability | SPEC-ERP-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-017 — Production order reference | SPEC-ERP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-018 — Warehouse/location mapping | SPEC-ERP-001 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-019 — UOM mapping | SPEC-ERP-001 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-020 — Lot/serial mapping | SPEC-ERP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-021 — Transaction command ledger | SPEC-ERP-001 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-022 — Inbound event ledger | SPEC-ERP-001 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-023 — Async default | SPEC-ERP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-024 — No distributed 2PC | SPEC-ERP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-025 — Reconciliation | SPEC-ERP-001 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-026 — Failure states | SPEC-ERP-001 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-027 — Manual recovery | SPEC-ERP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-028 — Security | SPEC-ERP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-029 — Observability | SPEC-ERP-001 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ERP-ARC-030 — Version compatibility | SPEC-ERP-001 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-001 — Supported API | SPEC-ERP-002 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-002 — Authentication | SPEC-ERP-002 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-003 — Item mapping | SPEC-ERP-002 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-004 — Supplier mapping | SPEC-ERP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-005 — Warehouse mapping | SPEC-ERP-002 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-006 — Purchase Order | SPEC-ERP-002 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-007 — Purchase Receipt | SPEC-ERP-002 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-008 — Stock Entry issue | SPEC-ERP-002 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-009 — Stock return | SPEC-ERP-002 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-010 — Batch/serial | SPEC-ERP-002 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-011 — Finished goods | SPEC-ERP-002 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-012 — Quality status projection | SPEC-ERP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-013 — Production order reference | SPEC-ERP-002 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-014 — External doc names | SPEC-ERP-002 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-015 — Submit/cancel semantics | SPEC-ERP-002 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-016 — Duplicate prevention | SPEC-ERP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-017 — Customization minimization | SPEC-ERP-002 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-018 — Custom field policy | SPEC-ERP-002 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-019 — Rate limiting | SPEC-ERP-002 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-020 — Attachment refs | SPEC-ERP-002 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-021 — Reconciliation | SPEC-ERP-002 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-022 — Health | SPEC-ERP-002 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-023 — Permission scope | SPEC-ERP-002 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| ENXT-FR-024 — No compliance delegation | SPEC-ERP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-001 — SAP instance profile | SPEC-ERP-003 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-002 — Auth | SPEC-ERP-003 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-003 — Product master | SPEC-ERP-003 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-004 — Material stock | SPEC-ERP-003 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-005 — Material document | SPEC-ERP-003 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-006 — Goods receipt | SPEC-ERP-003 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-007 — Goods issue | SPEC-ERP-003 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-008 — Transfer posting | SPEC-ERP-003 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-009 — Reversal | SPEC-ERP-003 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-010 — Movement mapping | SPEC-ERP-003 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-011 — Plant/storage location | SPEC-ERP-003 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-012 — Material/UOM | SPEC-ERP-003 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-013 — Batch/serial | SPEC-ERP-003 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-014 — Production order | SPEC-ERP-003 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-015 — Blocked/released stock | SPEC-ERP-003 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-016 — Posting date | SPEC-ERP-003 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-017 — External transaction ref | SPEC-ERP-003 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-018 — OData batch | SPEC-ERP-003 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-019 — Error mapping | SPEC-ERP-003 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-020 — CSRF/session handling | SPEC-ERP-003 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-021 — Throttling/retry | SPEC-ERP-003 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-022 — API version profile | SPEC-ERP-003 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-023 — Custom BAPI/RFC | SPEC-ERP-003 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-024 — Reconciliation | SPEC-ERP-003 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SAP-FR-025 — No SAP regulatory authority | SPEC-ERP-003 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-001 — Adapter families | SPEC-ERP-004 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-002 — Oracle REST profile | SPEC-ERP-004 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-003 — Oracle inventory transaction | SPEC-ERP-004 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-004 — Oracle receipt | SPEC-ERP-004 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-005 — Oracle lot/serial | SPEC-ERP-004 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-006 — Oracle privileges | SPEC-ERP-004 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-007 — Oracle API release | SPEC-ERP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-008 — Dynamics integration pattern | SPEC-ERP-004 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-009 — Dynamics product entity | SPEC-ERP-004 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-010 — Dynamics inventory | SPEC-ERP-004 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-011 — Dynamics company/legal entity | SPEC-ERP-004 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-012 — Dynamics entity versioning | SPEC-ERP-004 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-013 — Custom REST adapter | SPEC-ERP-004 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-014 — Custom SOAP adapter | SPEC-ERP-004 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-015 — Custom file adapter | SPEC-ERP-004 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-016 — Custom DB integration | SPEC-ERP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-017 — Canonical DTO mapping | SPEC-ERP-004 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-018 — Capabilities | SPEC-ERP-004 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-019 — External business error | SPEC-ERP-004 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-020 — Transport failure | SPEC-ERP-004 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-021 — Idempotency | SPEC-ERP-004 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-022 — Reconciliation | SPEC-ERP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-023 — Contract tests | SPEC-ERP-004 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MULTI-FR-024 — No unverified connector | SPEC-ERP-004 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-001 — Master-data catalogue | SPEC-ERP-005 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-002 — Field ownership | SPEC-ERP-005 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-003 — Mapping status | SPEC-ERP-005 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-004 — Initial sync | SPEC-ERP-005 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-005 — Incremental sync | SPEC-ERP-005 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-006 — External change detection | SPEC-ERP-005 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-007 — GxP change propagation | SPEC-ERP-005 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-008 — Identity matching | SPEC-ERP-005 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-009 — Duplicate detection | SPEC-ERP-005 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-010 — UOM mapping | SPEC-ERP-005 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-011 — Plant/site mapping | SPEC-ERP-005 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-012 — Warehouse mapping | SPEC-ERP-005 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-013 — Supplier mapping | SPEC-ERP-005 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-014 — Product/material mapping | SPEC-ERP-005 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-015 — Reference-data mapping | SPEC-ERP-005 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-016 — Effective dates | SPEC-ERP-005 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-017 — Suspension | SPEC-ERP-005 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-018 — Conflict queue | SPEC-ERP-005 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-019 — Approval | SPEC-ERP-005 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-020 — Bulk approval restriction | SPEC-ERP-005 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-021 — Mapping hash/version | SPEC-ERP-005 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-022 — Sync checkpoint | SPEC-ERP-005 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-023 — Replay | SPEC-ERP-005 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-024 — Delete semantics | SPEC-ERP-005 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-025 — Reconciliation | SPEC-ERP-005 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-026 — Data quality metrics | SPEC-ERP-005 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-027 — Audit | SPEC-ERP-005 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MDS-FR-028 — Migration | SPEC-ERP-005 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-001 — Canonical integration message | SPEC-ERP-006 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-002 — Error taxonomy | SPEC-ERP-006 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-003 — Retry classification | SPEC-ERP-006 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-004 — Exponential backoff | SPEC-ERP-006 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-005 — Maximum attempts | SPEC-ERP-006 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-006 — Idempotency key | SPEC-ERP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-007 — Payload hash | SPEC-ERP-006 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-008 — Uncertain timeout | SPEC-ERP-006 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-009 — External correlation | SPEC-ERP-006 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-010 — Inbound dedupe | SPEC-ERP-006 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-011 — Out-of-order events | SPEC-ERP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-012 — Dead letter | SPEC-ERP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-013 — Manual replay | SPEC-ERP-006 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-014 — Corrected command | SPEC-ERP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-015 — Cancellation | SPEC-ERP-006 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-016 — Compensation | SPEC-ERP-006 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-017 — Reconciliation types | SPEC-ERP-006 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-018 — Reconciliation snapshot | SPEC-ERP-006 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-019 — Auto-resolve | SPEC-ERP-006 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-020 — Integration hold | SPEC-ERP-006 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-021 — SLA/aging | SPEC-ERP-006 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-022 — Circuit breaker | SPEC-ERP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-023 — Bulk jobs | SPEC-ERP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-024 — Rate limiting | SPEC-ERP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-025 — Security event | SPEC-ERP-006 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-026 — Observability | SPEC-ERP-006 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-027 — Audit | SPEC-ERP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-028 — Retention | SPEC-ERP-006 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-029 — Chaos testing | SPEC-ERP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| INT-FR-030 — No silent success | SPEC-ERP-006 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |

Update the columns as work proceeds; the authoritative record is `traceability/TRACEABILITY_MASTER.csv` and `status/build-status.json`.
