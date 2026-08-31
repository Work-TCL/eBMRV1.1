# Database Migration Standard

**Derived from:** Document 100 (SPEC-ENG-004) — controlled source in `specs/`
**Purpose:** Migration authoring, safety, backfill and rollback rules.
**Requirements:** MIG-FR-001..032 (32)

> This file is the working engineering standard. The controlled source is Document 100; where the two
> differ, the specification wins and this file is corrected.

## Requirements

| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| MIG-FR-001 | Migration ownership | Only owning service/app migration package changes its authoritative schema. | Data ownership. |
| MIG-FR-002 | Version order | Migrations have deterministic unique ordered IDs and are immutable after production release. | Reproducibility. |
| MIG-FR-003 | Forward-first strategy | Production migrations designed forward-compatible; rollback usually app rollback/forward fix rather than destructive schema reversal. | Safety. |
| MIG-FR-004 | Expand-contract | Breaking schema evolution uses expand → dual compatibility/backfill → switch → contract after safe window. | Zero/low downtime. |
| MIG-FR-005 | No destructive history loss | Drop/truncate/delete of regulated/history data requires retention/migration approval and archival evidence. | Data integrity. |
| MIG-FR-006 | Backup precondition | Risk-relevant migration checks current backup/PITR and rollback/recovery readiness. | Recoverability. |
| MIG-FR-007 | Representative test | Migration tested against representative volume/cardinality/schema state. | Production realism. |
| MIG-FR-008 | Idempotency | Migration runner can detect applied state; rerun behavior explicit and safe. | Operational reliability. |
| MIG-FR-009 | Transactional DDL | Use transaction where supported/safe; nontransactional steps explicitly staged/recoverable. | Atomicity. |
| MIG-FR-010 | Lock analysis | Estimate table locks/rewrite duration/IO/WAL impact for large table changes. | Availability. |
| MIG-FR-011 | Online index | Use concurrent/online patterns when available and justified; failures leave recoverable state. | Availability. |
| MIG-FR-012 | Backfill | Large data backfills chunked/checkpointed/rate-limited with deterministic transform version. | Scale. |
| MIG-FR-013 | Backfill audit | Migration-generated regulated changes marked as migration provenance, not user actions. | Traceability. |
| MIG-FR-014 | Checksums/reconciliation | Data migration/backfill records counts/hashes/control totals before/after where material. | Accuracy. |
| MIG-FR-015 | Constraints | New NOT NULL/FK/check constraints introduced safely after data compatibility/backfill. | Integrity. |
| MIG-FR-016 | Default changes | Avoid table-rewrite defaults or hidden semantics; assess existing row behavior explicitly. | Safety. |
| MIG-FR-017 | Enum/state evolution | State/enum changes preserve historical readability and old worker compatibility during rollout. | Compatibility. |
| MIG-FR-018 | App compatibility | Document minimum/maximum app versions compatible with schema during rolling deploy. | Release safety. |
| MIG-FR-019 | MariaDB/Frappe migrations | Frappe patches/migrations follow same version/evidence discipline; projection tables may rebuild rather than complex migrate where safer. | Framework. |
| MIG-FR-020 | PostgreSQL migrations | GxP migrations executed by dedicated migration role; runtime service role has no DDL. | Security. |
| MIG-FR-021 | Object metadata | Object/evidence metadata schema migrations cannot orphan stored evidence. | Evidence. |
| MIG-FR-022 | Event schema coordination | Migration requiring event/API contract change coordinates deployment order and compatibility. | Distributed systems. |
| MIG-FR-023 | Temporal compatibility | Workflow code/schema changes account for in-flight histories/activity payloads. | Orchestration. |
| MIG-FR-024 | Migration dry run | Major migration supports staging/restore-copy rehearsal with timing/evidence. | Confidence. |
| MIG-FR-025 | Failure recovery | Runbook states partial-step detection, resume/repair/restore criteria. | Recovery. |
| MIG-FR-026 | No manual prod SQL | Manual DDL/DML in production prohibited except controlled emergency repair captured into subsequent migration/change record. | Control. |
| MIG-FR-027 | Reconciliation gate | Service not healthy after migration until mandatory schema/data checks pass. | Fail closed. |
| MIG-FR-028 | Migration evidence | Store source commit, migration IDs, start/end, runner, environment, result, counts/checks, failures. | Validation. |
| MIG-FR-029 | Retention-aware contract | Dropped old columns/tables only after retention/consumer/deployment compatibility analysis. | Governance. |
| MIG-FR-030 | Customer upgrade path | Every supported version has documented upgrade path or explicit intermediate hop. | Commercial support. |
| MIG-FR-031 | Downgrade semantics | Downgrade support explicitly stated; never imply app image rollback makes DB downgrade safe. | Honesty. |
| MIG-FR-032 | Validation impact | GxP schema/data migrations link change impact/revalidation requirements. | Validated state. |

## Enforcement

See `docs/generated/33_CODING_STANDARD_COMPLIANCE_MATRIX.md`,
`docs/generated/34_ARCHITECTURE_GUARDRAIL_MATRIX.md` and `.github/workflows/ci.yml`.

## Tests

- drop regulated column blocked
- large NOT NULL migration expand-contract
- chunked backfill resume
- migration checksum drift
- rolling old/new app compatibility
- MariaDB projection rebuild
- failed concurrent index
- PITR readiness check
