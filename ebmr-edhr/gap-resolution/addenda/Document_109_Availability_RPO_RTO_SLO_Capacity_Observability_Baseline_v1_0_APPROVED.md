# US eBMR / eDHR Regulated Manufacturing Platform
## Document 109 — Availability, RPO/RTO, Performance SLO, Capacity & Observability Baseline — v1.0 APPROVED

**Specification ID:** SPEC-DATA-012
**Status:** APPROVED v1.0 (construction baseline) — approvers of record: Product Owner, SRE Lead and Validation Lead; per-deployment values require Customer Quality approval
**Closes:** SG-006, SG-008, SG-016
**Approval:** Approved by the Project Owner during construction review on 2026-08-21. A formal Part 11 signature record must be captured in the QMS against this version before validated release; the approval block below is the record of the construction decision.

**Primary Dependencies:** Document 76 (backup/PITR/DR), Document 78 (performance/capacity/SLO/SRE), Document 91 (DR qualification), Document 93 (performance qualification), Document 86 (infrastructure qualification), Document 67 (security monitoring)

---

# 0. Why this document exists

Documents 76, 78, 91 and 93 all require RPO/RTO and p95/p99 targets to exist and be tested, and each defers the numbers to customer approval. A qualification protocol without numeric acceptance criteria cannot objectively pass or fail. This document supplies a **platform default tier model** that a deployment contract may override, so that DR and performance qualification have acceptance limits from day one.

# 1. Component recovery tiers (PROPOSED defaults)

| Tier | Components | RPO | RTO | Rationale |
|---|---|---|---|---|
| T0 — Regulated authoritative | PostgreSQL GxP state, audit stream, record versions, outbox, signature records | **0 (zero committed-transaction loss)** via synchronous replication or equivalent | ≤ 4 h | A committed regulated record must never be lost; §11.10(c) protection of records. |
| T1 — Immutable evidence | Object/WORM evidence store, vault manifests | 0 (versioned, replicated) | ≤ 8 h | Evidence must remain retrievable and verifiable. |
| T2 — Application/UI | Frappe/MariaDB configuration, workflow metadata | ≤ 15 min | ≤ 8 h | Rebuildable from configuration baseline plus backup. |
| T3 — Orchestration | Temporal history/state | ≤ 15 min | ≤ 8 h | Not regulatory truth; workflows resume from authoritative state (Doc 74). |
| T4 — Derived | Read models, search, cache, analytics projections | Rebuildable (no RPO commitment) | ≤ 24 h (degraded reporting acceptable) | Fully rebuildable from authoritative source (Doc 75). |
| T5 — Edge | Edge gateway buffers | Local durability ≥ 72 h offline (configurable per site) | ≤ 4 h to restore upstream flow | Store-and-forward protects OT continuity (Doc 45). |

**Interpretation rule.** RPO 0 for T0 means no acknowledged, committed regulated transaction may be lost. It does not promise zero in-flight request loss; a rejected or unacknowledged command is simply not committed and may be safely retried under the idempotency rule.

# 2. Availability objectives (PROPOSED)

| Deployment model | Monthly availability objective for regulated execution paths | Planned maintenance |
|---|---|---|
| Dedicated SaaS | 99.5 % | Announced windows excluded from the objective; never during a customer's declared production window without agreement |
| Customer private cloud | 99.5 % (customer infrastructure dependent) | Customer-scheduled |
| On-premise / plant | Defined per site; edge buffering must cover the site's maximum planned outage | Site-scheduled |

Availability of *derived* surfaces (reporting, search, analytics) is explicitly lower and must never block a regulated action.

# 3. Performance SLOs by operation class (PROPOSED)

Measured server-side at the GxP API boundary, steady-state load, excluding client network.

| Operation class | Examples | p95 | p99 | Notes |
|---|---|---|---|---|
| OC-1 Interactive read | batch execution view, step list, material lookup | 300 ms | 800 ms | Operator-facing; slow reads cause workarounds |
| OC-2 Regulated mutation (no signature) | record step result, start step, place hold | 500 ms | 1.2 s | Includes policy, rules, transaction, audit, outbox |
| OC-3 Regulated mutation (with signature) | approve, verify, release | 1.5 s | 3 s | Excludes the human step-up interaction time |
| OC-4 Policy/authorization decision | internal policy call | 50 ms | 150 ms | Called on every regulated action |
| OC-5 Rules/calculation evaluation | yield, tolerance, eligibility | 200 ms | 600 ms | Deterministic decimal evaluation |
| OC-6 Event publish lag (commit → bus) | outbox publisher | 2 s | 10 s | Alert threshold below the SLO |
| OC-7 Projection lag (commit → Frappe read model) | projection updater | 5 s | 30 s | Staleness flag shown in UI beyond p99 |
| OC-8 Search/report query | audit search, trending | 2 s | 8 s | Never on a regulated decision path |
| OC-9 Evidence write | file/evidence put + digest | 3 s | 10 s | Size-dependent; measured per MB tier |
| OC-10 Edge upload acceptance | buffered batch upload | 5 s | 20 s | Per upload window, not per sample |

# 4. Capacity baseline (PROPOSED reference profile)

| Dimension | Reference value | Basis |
|---|---|---|
| Concurrent execution users per site | 150 | Reference plant profile; scale unit defined per deployment |
| Regulated mutations per hour (peak) | 20 000 | Sizing input for transaction, audit and outbox throughput |
| Audit events per year | ≥ 200 million | Drives Doc 70 partitioning of `gxp_audit_event` |
| Edge samples per second per gateway | 500 | Drives buffer sizing and upload batching |
| Evidence objects per batch | 200 (avg), 2 000 (max) | Drives manifest and object-store sizing |
| Retention horizon online | 24 months hot, remainder archived | Interacts with Document 108 classes |

# 5. Observability baseline — mandatory signal classes

Every module inherits these signal classes; modules add domain signals on top. This closes SG-016 for the specifications that state none.

| Signal class | Required metrics | Required alerts |
|---|---|---|
| Availability | request rate, error rate, saturation per service | error-rate burn against SLO |
| Latency | p50/p95/p99 per operation class | p99 breach sustained beyond window |
| Transaction integrity | commits, rollbacks, stale-version rejections, fail-closed rejections | abnormal fail-closed rate (dependency outage) |
| Outbox | pending depth, publish lag, retry count, dead letters | `OutboxLagExceeded`, dead-letter growth |
| Projection | lag, rebuild state, stale count | `ProjectionLagExceeded`, `ProjectionStaleDetected` |
| Signature | challenges created/completed/expired/failed | failure or expiry spike (usability or attack signal) |
| Policy | decision latency, deny rate by reason | deny-rate anomaly, evaluation unavailability |
| Integration | inbound/outbound success, retry, reconciliation exceptions, DLQ | reconciliation exception ageing |
| Edge | gateway online state, buffer depth, time-sync drift, replay rejects | buffer near capacity, clock drift beyond tolerance |
| Evidence/WORM | write success, digest verification failures, lock failures | any digest verification failure (severity 1) |
| Backup/DR | backup success, restore test result, replication lag, `RPOAtRisk` | RPO at risk, missed backup, failed restore test |
| Security | authn failures, privilege elevation, break-glass use, anomaly events | per Document 67 incident triggers |

# 6. Functional requirements

| ID | Requirement | Detailed behaviour | Acceptance intent |
|---|---|---|---|
| AVL-FR-001 | Tier assignment | Every deployed component is assigned a recovery tier; unassigned components fail the infrastructure qualification. | IQ check. |
| AVL-FR-002 | RPO enforcement | T0 uses a replication/commit configuration that makes committed-transaction loss impossible under the declared failure modes. | DR test evidence. |
| AVL-FR-003 | RTO measurement | Restore and failover drills measure actual RTO against the tier target and record the evidence. | Document 91 evidence. |
| AVL-FR-004 | SLO declaration | Every API operation is mapped to an operation class; unmapped operations fail the contract gate. | CI check. |
| AVL-FR-005 | SLO measurement | p95/p99 measured continuously and reported per class. | Dashboard reproducible. |
| AVL-FR-006 | Performance qualification | Document 93 executes against these numbers as acceptance criteria. | Objective pass/fail. |
| AVL-FR-007 | Capacity headroom | Alerting triggers before capacity limits are reached, not after. | Threshold test. |
| AVL-FR-008 | Degraded-mode rules | Derived-surface unavailability must never block a regulated action; regulated dependency unavailability must fail closed. | Both tests pass. |
| AVL-FR-009 | Per-deployment override | Contractual overrides are recorded as configuration with customer approval and drive that deployment's qualification limits. | Override traceable. |
| AVL-FR-010 | Observability inheritance | Every module emits the mandatory signal classes; a module without them fails the release gate. | CI/release check. |

# 7. Test catalogue

1. Tier T0 failover: committed transactions all present after failover (RPO 0 proof).
2. Restore drill per tier measured against RTO.
3. PITR to a target timestamp with reconciliation evidence.
4. Each operation class load-tested against p95/p99.
5. Outbox and projection lag alerting fires before SLO breach.
6. Derived-surface outage: regulated actions still succeed.
7. Regulated dependency outage: regulated actions fail closed with the correct code.
8. Edge offline for the declared buffer window then reconnect: no evidence loss, no duplicates.
9. Capacity soak at reference profile for the declared duration.
10. Observability: each mandatory signal class present for every deployed module.

# 8. Validation impact

These numbers become the acceptance criteria for Documents 91 (DR) and 93 (performance) and inputs to Document 86 (infrastructure qualification). Changing a tier or SLO after approval is a revalidation trigger (Document 96).

# 9. Acceptance criteria

1. Every component has a tier; every operation has a class.
2. DR and performance qualification protocols cite these numbers.
3. All §7 tests pass at the reference profile.
4. Per-deployment overrides recorded and approved before that deployment's qualification.

# 10. Claude Code / Codex prohibitions

- Do not weaken a tier or SLO to make a test pass.
- Do not implement a degraded mode that commits regulated state without its audit/outbox companion.
- Do not treat derived-surface availability as a regulated dependency, or vice versa.

# 11. Approval block

| Role | Name | Decision | Date | Signature reference |
|---|---|---|---|---|
| Product Owner |  |  |  |  |
| SRE Lead |  |  |  |  |
| Validation Lead |  |  |  |  |
| Customer Quality (per deployment) |  |  |  |  |
