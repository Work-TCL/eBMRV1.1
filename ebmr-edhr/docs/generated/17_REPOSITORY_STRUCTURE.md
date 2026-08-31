# 17 — Repository Structure

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** The monorepo layout Claude Code must create, reconciled with the structures declared inside the specifications.

---

The controlled specifications repeatedly declare concrete paths (`services/gxp-api/src/modules/...`, `apps/ebmr_frappe/...`, `contracts/events/...`, `validation/requirements/...`). Those paths take precedence over any generic skeleton (source precedence rule 3 > 5). See `docs/adr/ADR-0001-repository-layout.md`.

```text
ebmr-edhr/
├── CLAUDE.md
├── README.md
├── PACKAGE_MANIFEST.md
│
├── .claude/
│   ├── rules/                      # modular agent rules (11 files)
│   └── settings.example.json
│
├── .github/
│   ├── CODEOWNERS
│   ├── pull_request_template.md
│   └── workflows/ci.yml
│
├── specs/                          # controlled baseline, read-only to the agent
│   ├── MASTER_00_eBMR_eDHR_Document_Index_and_Usage_Guide.md
│   ├── Documents_01_105/
│   ├── Specification_Authoring_Standard_Implementation_Ready_v1_0.md
│   └── ClaudeCode_Master_Project_Construction_Instructions_v1_7_FINAL_Documents_01_105.md
│
├── docs/
│   ├── generated/                  # Phase-0 artefacts (this directory)
│   ├── adr/
│   ├── engineering/                # coding/branching/migration/testing/CI-CD/SBOM standards
│   ├── runbooks/
│   └── validation/
│
├── prompts/                        # dependency-ordered Claude Code prompts
├── work-packages/                  # WP-00 … WP-14
│
├── apps/
│   └── ebmr_frappe/                # custom Frappe app ONLY — never a core fork
│       ├── ebmr/
│       │   ├── common/
│       │   ├── pharma/
│       │   ├── device/
│       │   ├── combination/
│       │   ├── qc/
│       │   ├── qms/
│       │   ├── execution/
│       │   └── integrations/
│       └── tests/
│
├── services/
│   ├── gxp-api/                    # GxP Core logical services (Doc 02 §11)
│   │   ├── src/modules/
│   │   │   ├── mutation/            # Doc 03 Mutation Gateway
│   │   │   ├── identity/            # Doc 07 identity context
│   │   │   ├── policy/              # Doc 07 authorization/qualification/SoD
│   │   │   ├── signature/           # Doc 04 Part 11 signature
│   │   │   ├── audit/               # Doc 05 immutable audit ledger
│   │   │   ├── vault/               # Doc 06 record version vault
│   │   │   ├── rules/               # Doc 08 rules & calculation
│   │   │   ├── product/ recipe/ batch/ execution/ dhr/    # Docs 09–12
│   │   │   ├── genealogy/ review/ release/ packaging/ yield/   # Docs 13–17
│   │   │   ├── procurement/ materials/ inventory/ dispensing/ consumption/  # Docs 18–22
│   │   │   ├── qc/ lims/ oos/       # Docs 23–25
│   │   │   ├── qms/                 # Docs 26–37
│   │   │   ├── equipment/ cleaning/ aseptic/ em/ sterilization/  # Docs 38–42
│   │   │   ├── ddcp/                # Docs 54–57
│   │   │   └── postmarket/          # Docs 58–60
│   │   ├── migrations/
│   │   └── test/
│   ├── workers/                    # Temporal workers (Doc 74)
│   ├── platform/                   # platform/ops services (Docs 75–78)
│   ├── security/                   # security services (Docs 61–68)
│   ├── integration-gateway/        # ERP/LIMS integration (Docs 48–53)
│   └── ai-gateway/                 # advisory AI only (Doc 105)
│
├── connectors/
│   ├── lims/
│   └── label-printing/
│
├── edge/
│   ├── gateway/
│   ├── drivers/
│   ├── buffering/
│   └── peripherals/
│
├── contracts/
│   ├── openapi/
│   ├── events/
│   └── schemas/
│
├── packages/
│   ├── data-contracts/
│   ├── security-contracts/
│   ├── domain-types/
│   ├── testing/
│   └── observability/
│
├── infrastructure/
│   ├── kubernetes/
│   ├── terraform/
│   ├── security/
│   └── observability/
│
├── validation/
│   ├── requirements/
│   ├── protocols/
│   ├── evidence/
│   ├── infrastructure/
│   └── security/
│
├── tests/
│   ├── contract/
│   ├── integration/
│   ├── e2e/
│   ├── security/
│   └── infrastructure/
│
└── tooling/
    ├── generators/
    ├── guardrails/
    └── scripts/
```

## Path declarations found in the controlled specifications

| Document | Declared paths |
|---|---|
| 01 | `platform/`<br>`├── frappe/`<br>`├── ebmr_app/`<br>`│   ├── common/`<br>`│   ├── combination/`<br>`│   ├── device/` |
| 03 | `services/gxp-api/`<br>`├── src/`<br>`│   ├── modules/`<br>`│   │   └── mutation/`<br>`│   │       └── handlers/`<br>`│   ├── clients/` |
| 04 | `services/signature/`<br>`├── src/`<br>`│   └── idp/`<br>`├── migrations/`<br>`├── openapi/`<br>`└── test/` |
| 05 | `services/audit/`<br>`├── src/`<br>`│   └── retention/`<br>`├── migrations/`<br>`├── test-vectors/`<br>`└── test/` |
| 06 | `services/gxp-api/src/modules/vault/`<br>`├── repositories/`<br>`packages/canonicalization/`<br>`├── src/`<br>`├── test-vectors/` |
| 07 | `services/gxp-api/src/modules/iam/`<br>`infrastructure/keycloak/`<br>`├── realms/`<br>`├── clients/`<br>`├── authentication-flows/`<br>`└── reference-mappings/` |
| 08 | `services/gxp-api/src/modules/rules/`<br>`├── evaluator/`<br>`packages/rule-sdk/`<br>`├── schemas/`<br>`├── compiler/`<br>`└── fixtures/` |
| 09 | `apps/ebmr_frappe/ebmr/product/`<br>`services/gxp-api/src/modules/product/`<br>`contracts/openapi/product.yaml`<br>`contracts/events/product/`<br>`validation/requirements/product/` |
| 10 | `apps/ebmr_frappe/ebmr/recipe/`<br>`services/gxp-api/src/modules/recipe/`<br>`services/gxp-api/src/modules/snapshot/`<br>`contracts/openapi/recipe.yaml`<br>`contracts/events/recipe/`<br>`packages/recipe-graph/` |
| 11 | `services/gxp-api/src/modules/batch/`<br>`services/gxp-api/src/modules/execution/`<br>`services/workers/src/workflows/batch/`<br>`apps/ebmr_frappe/ebmr/execution/`<br>`contracts/events/batch/`<br>`validation/requirements/execution/` |
| 12 | `services/gxp-api/src/modules/device-history/`<br>`apps/ebmr_frappe/ebmr/device/`<br>`contracts/events/device/`<br>`validation/requirements/device-history/` |
| 13 | `services/gxp-api/src/modules/genealogy/`<br>`packages/genealogy-model/`<br>`apps/ebmr_frappe/ebmr/genealogy/`<br>`contracts/events/genealogy/` |
| 14 | `services/gxp-api/src/modules/qa-review/`<br>`services/workers/src/qa-indexer/`<br>`apps/ebmr_frappe/ebmr/qa_review/`<br>`contracts/events/qa-review/` |
| 15 | `services/gxp-api/src/modules/release/`<br>`apps/ebmr_frappe/ebmr/release/`<br>`contracts/events/release/`<br>`validation/requirements/release/` |
| 16 | `services/gxp-api/src/modules/packaging/`<br>`apps/ebmr_frappe/ebmr/packaging/`<br>`connectors/label-printing/`<br>`contracts/events/packaging/` |
| 17 | `services/gxp-api/src/modules/manufacturing-calculations/`<br>`services/gxp-api/src/modules/reconciliation/`<br>`apps/ebmr_frappe/ebmr/reconciliation/`<br>`contracts/events/reconciliation/` |
| 18 | `services/gxp-api/src/modules/supplier-quality/`<br>`services/gxp-api/src/modules/procurement/`<br>`apps/ebmr_frappe/ebmr/supplier_quality/`<br>`apps/ebmr_frappe/ebmr/procurement/`<br>`connectors/erp/` |
| 19 | `services/gxp-api/src/modules/material-receipt/`<br>`services/gxp-api/src/modules/material-quality-status/`<br>`apps/ebmr_frappe/ebmr/receiving/`<br>`apps/ebmr_frappe/ebmr/sampling/` |
| 20 | `services/gxp-api/src/modules/inventory/`<br>`apps/ebmr_frappe/ebmr/warehouse/`<br>`contracts/events/inventory/` |
| 21 | `services/gxp-api/src/modules/dispensing/`<br>`apps/ebmr_frappe/ebmr/dispensing/`<br>`edge/gateway/plugins/balance/`<br>`connectors/label-printing/` |
| 22 | `services/gxp-api/src/modules/material-usage/`<br>`services/gxp-api/src/modules/destruction/`<br>`services/gxp-api/src/modules/material-reconciliation/`<br>`apps/ebmr_frappe/ebmr/material_usage/` |
| 23 | `services/gxp-api/src/modules/qc/`<br>`services/gxp-api/src/modules/sampling/`<br>`apps/ebmr_frappe/ebmr/qc/`<br>`apps/ebmr_frappe/ebmr/sampling/`<br>`contracts/events/qc/`<br>`validation/requirements/qc/` |
| 24 | `services/integration-gateway/src/lims/`<br>`connectors/lims/base/`<br>`connectors/lims/labware/`<br>`connectors/lims/starlims/`<br>`contracts/openapi/lims/`<br>`contracts/events/lims/` |
| 25 | `services/gxp-api/src/modules/oos/`<br>`services/gxp-api/src/modules/oot/`<br>`apps/ebmr_frappe/ebmr/oos/`<br>`apps/ebmr_frappe/ebmr/oot/`<br>`contracts/events/oos/`<br>`validation/requirements/oos/` |
| 26 | `services/gxp-api/src/modules/qms/deviation-and-investigation-management/`<br>`apps/ebmr_frappe/ebmr/qms/deviation-and-investigation-management/`<br>`contracts/events/qms/deviation-and-investigation-management/`<br>`validation/requirements/qms/deviation-and-investigation-management/` |
| 27 | `services/gxp-api/src/modules/qms/capa-management/`<br>`apps/ebmr_frappe/ebmr/qms/capa-management/`<br>`contracts/events/qms/capa-management/`<br>`validation/requirements/qms/capa-management/` |
| 28 | `services/gxp-api/src/modules/qms/nonconformance-management/`<br>`apps/ebmr_frappe/ebmr/qms/nonconformance-management/`<br>`contracts/events/qms/nonconformance-management/`<br>`validation/requirements/qms/nonconformance-management/` |
| 29 | `services/gxp-api/src/modules/qms/change-control/`<br>`apps/ebmr_frappe/ebmr/qms/change-control/`<br>`contracts/events/qms/change-control/`<br>`validation/requirements/qms/change-control/` |
| 30 | `services/gxp-api/src/modules/qms/document-control/`<br>`apps/ebmr_frappe/ebmr/qms/document-control/`<br>`contracts/events/qms/document-control/`<br>`validation/requirements/qms/document-control/` |
| 31 | `services/gxp-api/src/modules/qms/training-and-personnel-qualification/`<br>`apps/ebmr_frappe/ebmr/qms/training-and-personnel-qualification/`<br>`contracts/events/qms/training-and-personnel-qualification/`<br>`validation/requirements/qms/training-and-personnel-qualification/` |
| 32 | `services/gxp-api/src/modules/qms/supplier-quality---scar/`<br>`apps/ebmr_frappe/ebmr/qms/supplier-quality---scar/`<br>`contracts/events/qms/supplier-quality---scar/`<br>`validation/requirements/qms/supplier-quality---scar/` |
| 33 | `services/gxp-api/src/modules/qms/risk-management/`<br>`apps/ebmr_frappe/ebmr/qms/risk-management/`<br>`contracts/events/qms/risk-management/`<br>`validation/requirements/qms/risk-management/` |
| 34 | `services/gxp-api/src/modules/qms/internal-audit-management/`<br>`apps/ebmr_frappe/ebmr/qms/internal-audit-management/`<br>`contracts/events/qms/internal-audit-management/`<br>`validation/requirements/qms/internal-audit-management/` |
| 35 | `services/gxp-api/src/modules/qms/complaint-management/`<br>`apps/ebmr_frappe/ebmr/qms/complaint-management/`<br>`contracts/events/qms/complaint-management/`<br>`validation/requirements/qms/complaint-management/` |
| 36 | `services/gxp-api/src/modules/qms/recall---field-action-management/`<br>`apps/ebmr_frappe/ebmr/qms/recall---field-action-management/`<br>`contracts/events/qms/recall---field-action-management/`<br>`validation/requirements/qms/recall---field-action-management/` |
| 37 | `services/gxp-api/src/modules/qms/quality-metrics,-trending-and-effectiveness-checks/`<br>`apps/ebmr_frappe/ebmr/qms/quality-metrics,-trending-and-effectiveness-checks/`<br>`contracts/events/qms/quality-metrics,-trending-and-effectiveness-checks/`<br>`validation/requirements/qms/quality-metrics,-trending-and-effectiveness-checks/` |
| 38 | `services/gxp-api/src/modules/equipment-calibration-qualification-and-maintenance/`<br>`apps/ebmr_frappe/ebmr/equipment-calibration-qualification-and-maintenance/`<br>`edge/gateway/plugins/equipment-calibration-qualification-and-maintenance/`<br>`contracts/events/equipment-calibration-qualification-and-maintenance/`<br>`validation/requirements/equipment-calibration-qualification-and-maintenance/` |
| 39 | `services/gxp-api/src/modules/cleaning-sanitization-and-line-clearance/`<br>`apps/ebmr_frappe/ebmr/cleaning-sanitization-and-line-clearance/`<br>`edge/gateway/plugins/cleaning-sanitization-and-line-clearance/`<br>`contracts/events/cleaning-sanitization-and-line-clearance/`<br>`validation/requirements/cleaning-sanitization-and-line-clearance/` |
| 40 | `services/gxp-api/src/modules/sterile---aseptic-manufacturing-operations/`<br>`apps/ebmr_frappe/ebmr/sterile---aseptic-manufacturing-operations/`<br>`edge/gateway/plugins/sterile---aseptic-manufacturing-operations/`<br>`contracts/events/sterile---aseptic-manufacturing-operations/`<br>`validation/requirements/sterile---aseptic-manufacturing-operations/` |
| 41 | `services/gxp-api/src/modules/environmental-monitoring-and-cleanroom-state-control/`<br>`apps/ebmr_frappe/ebmr/environmental-monitoring-and-cleanroom-state-control/`<br>`edge/gateway/plugins/environmental-monitoring-and-cleanroom-state-control/`<br>`contracts/events/environmental-monitoring-and-cleanroom-state-control/`<br>`validation/requirements/environmental-monitoring-and-cleanroom-state-control/` |
| 42 | `services/gxp-api/src/modules/sterilization-cip-sip-and-sterile-filtration-management/`<br>`apps/ebmr_frappe/ebmr/sterilization-cip-sip-and-sterile-filtration-management/`<br>`edge/gateway/plugins/sterilization-cip-sip-and-sterile-filtration-management/`<br>`contracts/events/sterilization-cip-sip-and-sterile-filtration-management/`<br>`validation/requirements/sterilization-cip-sip-and-sterile-filtration-management/` |
| 43 | `edge/`<br>`├── runtime/`<br>`│   ├── supervisor/`<br>`│   ├── ingestion/`<br>`│   ├── normalization/`<br>`│   ├── forwarding/` |
| 44 | `edge/plugins/`<br>`├── base/`<br>`├── opcua/`<br>`├── modbus/`<br>`├── mqtt/`<br>`├── snmp/` |
| 49 | `connectors/erpnext/`<br>`├── src/`<br>`│   ├── client/`<br>`│   ├── auth/`<br>`│   ├── mappings/`<br>`│   ├── purchase/` |
| 58 | `services/gxp-api/src/modules/postmarket/surveillance/`<br>`services/gxp-api/src/modules/postmarket/signals/`<br>`apps/ebmr_frappe/ebmr/postmarket/surveillance/`<br>`contracts/events/postmarket/`<br>`validation/requirements/postmarket/` |
| 59 | `services/gxp-api/src/modules/postmarket/reportability/`<br>`services/integration-gateway/src/regulatory/emdr/`<br>`services/integration-gateway/src/regulatory/aems/`<br>`apps/ebmr_frappe/ebmr/postmarket/reportability/`<br>`contracts/regulatory/`<br>`validation/requirements/postmarket-reporting/` |
| 60 | `services/gxp-api/src/modules/postmarket/regulatory-operations/`<br>`apps/ebmr_frappe/ebmr/postmarket/regulatory_operations/`<br>`contracts/events/postmarket/`<br>`services/workers/src/regulatory-calendar/`<br>`validation/requirements/postmarket-operations/` |
| 61 | `services/security/security-architecture-threat-model-control-framework/`<br>`packages/security-contracts/`<br>`infrastructure/security/`<br>`apps/ebmr_frappe/ebmr/security/security-architecture-threat-model-control-framework/`<br>`validation/security/security-architecture-threat-model-control-framework/`<br>`tests/security/security-architecture-threat-model-control-framework/` |
| 62 | `services/security/identity-federation-sso-mfa-sessions-service-identities/`<br>`packages/security-contracts/`<br>`infrastructure/security/`<br>`apps/ebmr_frappe/ebmr/security/identity-federation-sso-mfa-sessions-service-identities/`<br>`validation/security/identity-federation-sso-mfa-sessions-service-identities/`<br>`tests/security/identity-federation-sso-mfa-sessions-service-identities/` |
| 63 | `services/security/privileged-access-support-access-break-glass-administrative-security/`<br>`packages/security-contracts/`<br>`infrastructure/security/`<br>`apps/ebmr_frappe/ebmr/security/privileged-access-support-access-break-glass-administrative-security/`<br>`validation/security/privileged-access-support-access-break-glass-administrative-security/`<br>`tests/security/privileged-access-support-access-break-glass-administrative-security/` |
| 64 | `services/security/application-api-ui-secure-runtime-engineering/`<br>`packages/security-contracts/`<br>`infrastructure/security/`<br>`apps/ebmr_frappe/ebmr/security/application-api-ui-secure-runtime-engineering/`<br>`validation/security/application-api-ui-secure-runtime-engineering/`<br>`tests/security/application-api-ui-secure-runtime-engineering/` |
| 65 | `services/security/secrets-management-pki-cryptography-key-lifecycle/`<br>`packages/security-contracts/`<br>`infrastructure/security/`<br>`apps/ebmr_frappe/ebmr/security/secrets-management-pki-cryptography-key-lifecycle/`<br>`validation/security/secrets-management-pki-cryptography-key-lifecycle/`<br>`tests/security/secrets-management-pki-cryptography-key-lifecycle/` |
| 66 | `services/security/network-tenant-deployment-isolation-zero-trust-architecture/`<br>`packages/security-contracts/`<br>`infrastructure/security/`<br>`apps/ebmr_frappe/ebmr/security/network-tenant-deployment-isolation-zero-trust-architecture/`<br>`validation/security/network-tenant-deployment-isolation-zero-trust-architecture/`<br>`tests/security/network-tenant-deployment-isolation-zero-trust-architecture/` |
| 67 | `services/security/security-logging-monitoring-incident-response-forensic-evidence/`<br>`packages/security-contracts/`<br>`infrastructure/security/`<br>`apps/ebmr_frappe/ebmr/security/security-logging-monitoring-incident-response-forensic-evidence/`<br>`validation/security/security-logging-monitoring-incident-response-forensic-evidence/`<br>`tests/security/security-logging-monitoring-incident-response-forensic-evidence/` |
| 68 | `services/security/secure-sdlc-software-supply-chain-sbom-vulnerability-release-security/`<br>`packages/security-contracts/`<br>`infrastructure/security/`<br>`apps/ebmr_frappe/ebmr/security/secure-sdlc-software-supply-chain-sbom-vulnerability-release-security/`<br>`validation/security/secure-sdlc-software-supply-chain-sbom-vulnerability-release-security/`<br>`tests/security/secure-sdlc-software-supply-chain-sbom-vulnerability-release-security/` |
| 69 | `infrastructure/enterprise-data-ownership-persistence-topology-data-lineage/`<br>`services/platform/enterprise-data-ownership-persistence-topology-data-lineage/`<br>`packages/data-contracts/`<br>`validation/infrastructure/enterprise-data-ownership-persistence-topology-data-lineage/`<br>`tests/infrastructure/enterprise-data-ownership-persistence-topology-data-lineage/`<br>`docs/runbooks/enterprise-data-ownership-persistence-topology-data-lineage/` |
| 70 | `infrastructure/postgresql-gxp-database-architecture-schema-partitioning-concurrency/`<br>`services/platform/postgresql-gxp-database-architecture-schema-partitioning-concurrency/`<br>`packages/data-contracts/`<br>`validation/infrastructure/postgresql-gxp-database-architecture-schema-partitioning-concurrency/`<br>`tests/infrastructure/postgresql-gxp-database-architecture-schema-partitioning-concurrency/`<br>`docs/runbooks/postgresql-gxp-database-architecture-schema-partitioning-concurrency/` |
| 71 | `infrastructure/frappe-mariadb-operational-database-projection-ui-data-architecture/`<br>`services/platform/frappe-mariadb-operational-database-projection-ui-data-architecture/`<br>`packages/data-contracts/`<br>`validation/infrastructure/frappe-mariadb-operational-database-projection-ui-data-architecture/`<br>`tests/infrastructure/frappe-mariadb-operational-database-projection-ui-data-architecture/`<br>`docs/runbooks/frappe-mariadb-operational-database-projection-ui-data-architecture/` |
| 72 | `infrastructure/immutable-evidence-object-storage-worm-archive-file-lifecycle/`<br>`services/platform/immutable-evidence-object-storage-worm-archive-file-lifecycle/`<br>`packages/data-contracts/`<br>`validation/infrastructure/immutable-evidence-object-storage-worm-archive-file-lifecycle/`<br>`tests/infrastructure/immutable-evidence-object-storage-worm-archive-file-lifecycle/`<br>`docs/runbooks/immutable-evidence-object-storage-worm-archive-file-lifecycle/` |
| 73 | `infrastructure/nats-jetstream-event-bus-transactional-outbox-async-contracts/`<br>`services/platform/nats-jetstream-event-bus-transactional-outbox-async-contracts/`<br>`packages/data-contracts/`<br>`validation/infrastructure/nats-jetstream-event-bus-transactional-outbox-async-contracts/`<br>`tests/infrastructure/nats-jetstream-event-bus-transactional-outbox-async-contracts/`<br>`docs/runbooks/nats-jetstream-event-bus-transactional-outbox-async-contracts/` |
| 74 | `infrastructure/temporal-durable-workflow-orchestration-architecture/`<br>`services/platform/temporal-durable-workflow-orchestration-architecture/`<br>`packages/data-contracts/`<br>`validation/infrastructure/temporal-durable-workflow-orchestration-architecture/`<br>`tests/infrastructure/temporal-durable-workflow-orchestration-architecture/`<br>`docs/runbooks/temporal-durable-workflow-orchestration-architecture/` |
| 75 | `infrastructure/caching-search-read-models-reporting-projections-analytics-data-access/`<br>`services/platform/caching-search-read-models-reporting-projections-analytics-data-access/`<br>`packages/data-contracts/`<br>`validation/infrastructure/caching-search-read-models-reporting-projections-analytics-data-access/`<br>`tests/infrastructure/caching-search-read-models-reporting-projections-analytics-data-access/`<br>`docs/runbooks/caching-search-read-models-reporting-projections-analytics-data-access/` |
| 76 | `infrastructure/backup-restore-point-in-time-recovery-disaster-recovery/`<br>`services/platform/backup-restore-point-in-time-recovery-disaster-recovery/`<br>`packages/data-contracts/`<br>`validation/infrastructure/backup-restore-point-in-time-recovery-disaster-recovery/`<br>`tests/infrastructure/backup-restore-point-in-time-recovery-disaster-recovery/`<br>`docs/runbooks/backup-restore-point-in-time-recovery-disaster-recovery/` |
| 77 | `infrastructure/cloud-neutral-deployment-kubernetes-on-prem-runtime-upgrade-architecture/`<br>`services/platform/cloud-neutral-deployment-kubernetes-on-prem-runtime-upgrade-architecture/`<br>`packages/data-contracts/`<br>`validation/infrastructure/cloud-neutral-deployment-kubernetes-on-prem-runtime-upgrade-architecture/`<br>`tests/infrastructure/cloud-neutral-deployment-kubernetes-on-prem-runtime-upgrade-architecture/`<br>`docs/runbooks/cloud-neutral-deployment-kubernetes-on-prem-runtime-upgrade-architecture/` |
| 78 | `infrastructure/performance-capacity-observability-slos-sre-operations/`<br>`services/platform/performance-capacity-observability-slos-sre-operations/`<br>`packages/data-contracts/`<br>`validation/infrastructure/performance-capacity-observability-slos-sre-operations/`<br>`tests/infrastructure/performance-capacity-observability-slos-sre-operations/`<br>`docs/runbooks/performance-capacity-observability-slos-sre-operations/` |
