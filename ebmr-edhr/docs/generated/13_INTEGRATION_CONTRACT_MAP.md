# 13 — Integration Contract Map

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** External systems, ownership boundary, contract, idempotency and reconciliation (Docs 24, 43–53).

---

| External system | Direction | Owning adapter | Contract source | GxP ownership rule | Idempotency | Reconciliation |
|---|---|---|---|---|---|---|
| ERPNext | bi-directional | services/integration-gateway/erpnext | Doc 49 | ERP owns commercial documents; GxP owns regulated state; ERP docstatus ≠ QA release | command_id ↔ ERPNext document reference; lookup before retry | posting ledger + exception report |
| SAP S/4HANA | bi-directional | services/integration-gateway/sap | Doc 50 | same as Doc 48 ownership matrix | external reference mapping per command | material document reconciliation |
| Oracle Fusion / Dynamics 365 / custom ERP | bi-directional | services/integration-gateway/{oracle,d365,custom} | Doc 51 | same as Doc 48 ownership matrix | external reference mapping per command | provider-specific reconciliation job |
| LIMS (generic) | inbound results / outbound samples | connectors/lims | Doc 24 | LIMS result is data; GxP acceptance command creates the regulated QC record | external_result_id dedupe | unaccepted/mismatched result report |
| Edge gateway / PLC / SCADA | inbound evidence, bounded commands | edge/gateway | Docs 43,44,45,47 | edge buffer is pre-authoritative; acceptance creates GxP truth | source event id + sequence + idempotency key | gap/sequence detection and replay ledger |
| Peripherals (scanner, balance, printer, tester) | inbound measurement / outbound label | edge/peripherals | Doc 46 | device identity registered; unknown source rejected/quarantined | reading id + station + timestamp | print/verification reconciliation (Doc 16) |
| Identity provider (SSO/MFA) | inbound assertions | platform/security/identity | Doc 62 | IdP authenticates; GxP Signature Service creates the regulatory signature record | nonce/challenge single use | session/authentication audit review |
| Regulatory submission gateway | outbound | services/domain-services/postmarket | Doc 59 | no autonomous submission; human authorization required | submission attempt id + ack | acknowledgement/rejection tracking |

## Universal integration rules

- No adapter writes to a GxP table. Adapters call integration commands (AG-13).
- Integration identities are non-human, narrowly scoped, and can never sign (MUT-FR-023 / SIG-FR-023).
- Every inbound message is idempotent by source id; replays are detected and rejected (MUT-FR-025).
- Timeout-uncertain outcomes are resolved by lookup, never by blind re-create (Doc 53).
- Every interface has a reconciliation job and an exception queue that a human owns (Doc 53).
- Interface changes require interface validation impact review (Doc 90).
