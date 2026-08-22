# 26 — RPO / RTO / Backup / Restore Matrix

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Recovery tiers and acceptance limits (approved baseline: Document 109).

---

| Tier | Components | RPO | RTO | Backup method | Restore verification | Qualification |
|---|---|---|---|---|---|---|
| T0 | PostgreSQL GxP state, audit, versions, outbox, signatures | 0 committed-transaction loss | ≤ 4 h | continuous archiving + PITR + synchronous replication | version counts, hashes, manifests, signature links (VLT-FR-027) | Doc 91 |
| T1 | Object/WORM evidence, vault manifests | 0 | ≤ 8 h | versioned replicated object storage + retention lock | digest verification of sampled and full manifests | Doc 91 |
| T2 | Frappe/MariaDB configuration and workflow metadata | ≤ 15 min | ≤ 8 h | snapshot + binlog | configuration fingerprint comparison | Doc 86/91 |
| T3 | Temporal history | ≤ 15 min | ≤ 8 h | managed backup | workflow resumption from authoritative state | Doc 91 |
| T4 | Read models, search, cache, analytics | rebuildable | ≤ 24 h | none required — rebuild | rebuild completeness reconciliation | Doc 91 |
| T5 | Edge gateway buffers | ≥ 72 h local durability | ≤ 4 h upstream restore | local persistent buffer | gap/sequence reconciliation on reconnect | Doc 90/91 |

## Rules
- Restore never resurrects a lawfully disposed record (Doc 108 RET-FR-013).
- Restore re-applies retention state and legal holds.
- Every restore drill produces retained evidence (RC-VALIDATION).
- `RPOAtRisk` alerting fires before the tier limit is breached.
