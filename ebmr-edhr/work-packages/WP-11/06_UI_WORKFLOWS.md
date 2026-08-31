# WP-11 — UI Workflows

Frappe screens never write regulated state directly; each action calls a GxP API operation. Projected GxP fields are read-only.

| UI surface | Doc | Module |
|---|---|---|
| Data Ownership Matrix | 69 | SPEC-DATA-001 |
| Projection Health | 69 | SPEC-DATA-001 |
| Data Dictionary | 69 | SPEC-DATA-001 |
| Migration Provenance | 69 | SPEC-DATA-001 |
| Cross-Store Consistency | 69 | SPEC-DATA-001 |
| Database/Schema Inventory | 70 | SPEC-DATA-002 |
| Partition Health | 70 | SPEC-DATA-002 |
| Connection/Lock Dashboard | 70 | SPEC-DATA-002 |
| Slow Query Dashboard | 70 | SPEC-DATA-002 |
| Integrity Checks | 70 | SPEC-DATA-002 |
| Migration History | 70 | SPEC-DATA-002 |
| Projection Sync Status | 71 | SPEC-DATA-003 |
| Frappe DB Health | 71 | SPEC-DATA-003 |
| Projection Rebuild | 71 | SPEC-DATA-003 |
| Stale Projection Indicators | 71 | SPEC-DATA-003 |
| Frappe Migration History | 71 | SPEC-DATA-003 |
| Evidence Browser (authorized metadata) | 72 | SPEC-DATA-004 |
| Upload/Quarantine | 72 | SPEC-DATA-004 |
| Integrity Status | 72 | SPEC-DATA-004 |
| Retention/Hold | 72 | SPEC-DATA-004 |
| Archive Tier | 72 | SPEC-DATA-004 |
| Evidence Manifest | 72 | SPEC-DATA-004 |
| Provider Migration | 72 | SPEC-DATA-004 |
| Event Stream Health | 73 | SPEC-DATA-005 |
| Outbox Lag | 73 | SPEC-DATA-005 |
| Consumer Lag | 73 | SPEC-DATA-005 |
| Dead Letters | 73 | SPEC-DATA-005 |
| Schema Registry | 73 | SPEC-DATA-005 |
| Replay Jobs | 73 | SPEC-DATA-005 |
| Workflow Operations | 74 | SPEC-DATA-006 |
| Stuck/Failed Activities | 74 | SPEC-DATA-006 |
| Timer/Deadline Operations | 74 | SPEC-DATA-006 |
| Worker Version/Task Queues | 74 | SPEC-DATA-006 |
| Replay Compatibility | 74 | SPEC-DATA-006 |
| Search | 75 | SPEC-DATA-007 |
| Index Health | 75 | SPEC-DATA-007 |
| Cache Health | 75 | SPEC-DATA-007 |
| Read Model Freshness | 75 | SPEC-DATA-007 |
| Async Exports | 75 | SPEC-DATA-007 |
| Analytics Cutoff | 75 | SPEC-DATA-007 |
| Backup Health | 76 | SPEC-DATA-008 |
| WAL/PITR Coverage | 76 | SPEC-DATA-008 |
| Restore Tests | 76 | SPEC-DATA-008 |
| DR Objectives | 76 | SPEC-DATA-008 |
| Failover/Incident | 76 | SPEC-DATA-008 |
| Recovery Validation | 76 | SPEC-DATA-008 |
| Deployment Inventory | 77 | SPEC-DATA-009 |
| Version Matrix | 77 | SPEC-DATA-009 |
| Install Preflight | 77 | SPEC-DATA-009 |
| Upgrade Dashboard | 77 | SPEC-DATA-009 |
| Drift | 77 | SPEC-DATA-009 |
| Capacity/Autoscaling | 77 | SPEC-DATA-009 |
| Post-Install Qualification | 77 | SPEC-DATA-009 |
| Executive Reliability | 78 | SPEC-DATA-010 |
| GxP API | 78 | SPEC-DATA-010 |
| Database | 78 | SPEC-DATA-010 |
| NATS/Outbox | 78 | SPEC-DATA-010 |
| Temporal | 78 | SPEC-DATA-010 |
| Edge Fleet | 78 | SPEC-DATA-010 |
| Object Evidence | 78 | SPEC-DATA-010 |
| Projection Freshness | 78 | SPEC-DATA-010 |
| Capacity Forecast | 78 | SPEC-DATA-010 |
| Backup/DR | 78 | SPEC-DATA-010 |
