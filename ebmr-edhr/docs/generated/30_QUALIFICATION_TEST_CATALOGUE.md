# 30 — Qualification Test Catalogue

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** IQ/OQ/PQ and specialised qualification scenarios extracted from Documents 83–96.

---


## IQ — Document 83 (SPEC-VAL-005)

**Requirements:** IQ-FR-001..021 (21)

| # | Scenario | Acceptance basis |
|---|---|---|
| 1 | wrong image digest | Document 83 acceptance criteria |
| 2 | unsupported DB version | Document 83 acceptance criteria |
| 3 | NTP missing | Document 83 acceptance criteria |
| 4 | backup absent | Document 83 acceptance criteria |
| 5 | cert expired | Document 83 acceptance criteria |
| 6 | forbidden path open | Document 83 acceptance criteria |
| 7 | validation endpoint points to prod ERP | Document 83 acceptance criteria |

## OQ — Document 84 (SPEC-VAL-006)

**Requirements:** OQ-FR-001..018 (18)

| # | Scenario | Acceptance basis |
|---|---|---|
| 1 | stale mutation denied | Document 84 acceptance criteria |
| 2 | signature wrong meaning | Document 84 acceptance criteria |
| 3 | audit old/new | Document 84 acceptance criteria |
| 4 | rounding vectors | Document 84 acceptance criteria |
| 5 | duplicate command | Document 84 acceptance criteria |
| 6 | worker restart | Document 84 acceptance criteria |
| 7 | unauthorized release | Document 84 acceptance criteria |

## PQ/UAT — Document 85 (SPEC-VAL-007)

**Requirements:** PQ-FR-001..020 (20)

| # | Scenario | Acceptance basis |
|---|---|---|
| 1 | untrained user blocked | Document 85 acceptance criteria |
| 2 | PFS batch scenario | Document 85 acceptance criteria |
| 3 | ERP unavailable | Document 85 acceptance criteria |
| 4 | signature flow | Document 85 acceptance criteria |
| 5 | batch deviation | Document 85 acceptance criteria |
| 6 | procedure/UI mismatch | Document 85 acceptance criteria |
| 7 | controlled UAT reuse | Document 85 acceptance criteria |

## Infrastructure Q — Document 86 (SPEC-VAL-008)

**Requirements:** INFQ-FR-001..020 (20)

| # | Scenario | Acceptance basis |
|---|---|---|
| 1 | prod/validation difference | Document 86 acceptance criteria |
| 2 | network deny | Document 86 acceptance criteria |
| 3 | managed DB failover | Document 86 acceptance criteria |
| 4 | NATS persistence | Document 86 acceptance criteria |
| 5 | Temporal reconnect | Document 86 acceptance criteria |
| 6 | clock alert | Document 86 acceptance criteria |
| 7 | object immutability | Document 86 acceptance criteria |

## Migration/Cutover Q — Document 87 (SPEC-VAL-009)

**Requirements:** MIGV-FR-001..022 (22)

| # | Scenario | Acceptance basis |
|---|---|---|
| 1 | duplicate legacy ID | Document 87 acceptance criteria |
| 2 | timezone conversion | Document 87 acceptance criteria |
| 3 | historic signature | Document 87 acceptance criteria |
| 4 | missing attachment | Document 87 acceptance criteria |
| 5 | quantity mismatch | Document 87 acceptance criteria |
| 6 | rejected record | Document 87 acceptance criteria |
| 7 | final delta | Document 87 acceptance criteria |

## Part 11 Q — Document 88 (SPEC-VAL-010)

**Requirements:** P11-FR-001..026 (26)

| # | Scenario | Acceptance basis |
|---|---|---|
| 1 | unauthorized record access | Document 88 acceptance criteria |
| 2 | audit old/new | Document 88 acceptance criteria |
| 3 | wrong workflow order | Document 88 acceptance criteria |
| 4 | invalid scanner source | Document 88 acceptance criteria |
| 5 | signature manifestation | Document 88 acceptance criteria |
| 6 | signature reassociation denied | Document 88 acceptance criteria |
| 7 | expired challenge | Document 88 acceptance criteria |
| 8 | archive retrieval | Document 88 acceptance criteria |

## Audit/Vault/Data Integrity Q — Document 89 (SPEC-VAL-011)

**Requirements:** DIV-FR-001..024 (24)

| # | Scenario | Acceptance basis |
|---|---|---|
| 1 | audit row modified/deleted | Document 89 acceptance criteria |
| 2 | hash chain break | Document 89 acceptance criteria |
| 3 | evidence replaced | Document 89 acceptance criteria |
| 4 | failed result retained | Document 89 acceptance criteria |
| 5 | correction history | Document 89 acceptance criteria |
| 6 | cold archive | Document 89 acceptance criteria |
| 7 | late Edge chronology | Document 89 acceptance criteria |

## Interface/Edge Q — Document 90 (SPEC-VAL-012)

**Requirements:** IFV-FR-001..024 (24)

| # | Scenario | Acceptance basis |
|---|---|---|
| 1 | duplicate ERP receipt | Document 90 acceptance criteria |
| 2 | wrong LIMS sample | Document 90 acceptance criteria |
| 3 | 72h Edge outage synthetic | Document 90 acceptance criteria |
| 4 | bad OPC quality | Document 90 acceptance criteria |
| 5 | unstable balance | Document 90 acceptance criteria |
| 6 | wrong barcode | Document 90 acceptance criteria |
| 7 | spoofed webhook | Document 90 acceptance criteria |
| 8 | command disabled | Document 90 acceptance criteria |

## Backup/Restore/DR Q — Document 91 (SPEC-VAL-013)

**Requirements:** DRV-FR-001..022 (22)

| # | Scenario | Acceptance basis |
|---|---|---|
| 1 | PITR | Document 91 acceptance criteria |
| 2 | standby failover | Document 91 acceptance criteria |
| 3 | object mismatch | Document 91 acceptance criteria |
| 4 | outbox recovery | Document 91 acceptance criteria |
| 5 | Temporal resume | Document 91 acceptance criteria |
| 6 | MariaDB rebuild | Document 91 acceptance criteria |
| 7 | key unavailable | Document 91 acceptance criteria |
| 8 | RPO exceeded | Document 91 acceptance criteria |

## Security Q — Document 92 (SPEC-VAL-014)

**Requirements:** SECQ-FR-001..024 (24)

| # | Scenario | Acceptance basis |
|---|---|---|
| 1 | cross-tenant BOLA | Document 92 acceptance criteria |
| 2 | MFA bypass | Document 92 acceptance criteria |
| 3 | SSRF | Document 92 acceptance criteria |
| 4 | malicious upload | Document 92 acceptance criteria |
| 5 | break-glass no signature | Document 92 acceptance criteria |
| 6 | expired cert | Document 92 acceptance criteria |
| 7 | unsigned image | Document 92 acceptance criteria |
| 8 | SIEM rule | Document 92 acceptance criteria |

## Performance/Load Q — Document 93 (SPEC-VAL-015)

**Requirements:** PERFQ-FR-001..024 (24)

| # | Scenario | Acceptance basis |
|---|---|---|
| 1 | 250 concurrent | Document 93 acceptance criteria |
| 2 | several-thousand-step batch | Document 93 acceptance criteria |
| 3 | millions audit/day | Document 93 acceptance criteria |
| 4 | long Edge catch-up | Document 93 acceptance criteria |
| 5 | DB failover | Document 93 acceptance criteria |
| 6 | NATS outage | Document 93 acceptance criteria |
| 7 | soak | Document 93 acceptance criteria |
| 8 | heavy report | Document 93 acceptance criteria |

## Exception handling — Document 94 (SPEC-VAL-016)

**Requirements:** VEX-FR-001..022 (22)

| # | Scenario | Acceptance basis |
|---|---|---|
| 1 | fail then fixed/retest | Document 94 acceptance criteria |
| 2 | wrong environment invalidates pass | Document 94 acceptance criteria |
| 3 | missing critical evidence | Document 94 acceptance criteria |
| 4 | accepted cosmetic issue | Document 94 acceptance criteria |
| 5 | critical defect blocks release | Document 94 acceptance criteria |

## VSR / release authorization — Document 95 (SPEC-VAL-017)

**Requirements:** VSR-FR-001..024 (24)

| # | Scenario | Acceptance basis |
|---|---|---|
| 1 | config mismatch | Document 95 acceptance criteria |
| 2 | open critical exception | Document 95 acceptance criteria |
| 3 | expired training | Document 95 acceptance criteria |
| 4 | DR missing | Document 95 acceptance criteria |
| 5 | security critical finding | Document 95 acceptance criteria |
| 6 | post-go-live smoke fail | Document 95 acceptance criteria |

## Periodic review — Document 96 (SPEC-VAL-018)

**Requirements:** VSM-FR-001..028 (28)

| # | Scenario | Acceptance basis |
|---|---|---|
| 1 | security patch targeted regression | Document 96 acceptance criteria |
| 2 | DB major upgrade | Document 96 acceptance criteria |
| 3 | release rule change | Document 96 acceptance criteria |
| 4 | IdP change Part11 retest | Document 96 acceptance criteria |
| 5 | expired DR qualification | Document 96 acceptance criteria |
| 6 | critical incident suspension | Document 96 acceptance criteria |
| 7 | decommission archive | Document 96 acceptance criteria |

## Rules
- A failed execution is immutable and handled through Document 94.
- Higher-risk functions require negative and failure-path evidence.
- Code coverage alone is never qualification evidence.
