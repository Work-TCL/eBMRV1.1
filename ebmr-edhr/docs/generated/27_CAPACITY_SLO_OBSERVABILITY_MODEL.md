# 27 — Capacity, SLO & Observability Model

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Operation classes, SLO targets, capacity reference profile and mandatory signal classes (Document 109).

---

| Class | Examples | p95 | p99 |
|---|---|---|---|
| OC-1 Interactive read | execution view, step list | 300 ms | 800 ms |
| OC-2 Regulated mutation | record result, start step, hold | 500 ms | 1.2 s |
| OC-3 Mutation with signature | approve, verify, release | 1.5 s | 3 s |
| OC-4 Policy decision | authorization call | 50 ms | 150 ms |
| OC-5 Rules/calculation | yield, tolerance, eligibility | 200 ms | 600 ms |
| OC-6 Event publish lag | outbox → bus | 2 s | 10 s |
| OC-7 Projection lag | commit → read model | 5 s | 30 s |
| OC-8 Search/report | audit search, trending | 2 s | 8 s |
| OC-9 Evidence write | object put + digest | 3 s | 10 s |
| OC-10 Edge upload | buffered batch acceptance | 5 s | 20 s |

## Capacity reference profile

- **Concurrent execution users per site:** 150
- **Regulated mutations per hour (peak):** 20 000
- **Audit events per year:** ≥ 200 million (drives partitioning)
- **Edge samples per second per gateway:** 500
- **Evidence objects per batch:** 200 avg / 2 000 max
- **Online retention horizon:** 24 months hot, remainder archived

## Mandatory signal classes (every module)

- availability
- latency by operation class
- transaction integrity (commits, rollbacks, fail-closed)
- outbox depth/lag/dead letters
- projection lag and staleness
- signature challenge outcomes
- policy decision latency and deny reasons
- integration retries and reconciliation exceptions
- edge gateway state, buffer depth, clock drift
- evidence digest verification failures
- backup/restore/replication and RPOAtRisk
- security events per Document 67
