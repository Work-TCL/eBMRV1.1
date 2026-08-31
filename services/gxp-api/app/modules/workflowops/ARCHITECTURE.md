# `workflowops` — Temporal Durable Workflow Orchestration Architecture (Document 74 / SPEC-DATA-006)

Document 74 declares **0 owned entities, 0 HTTP APIs, 5 events, no signatures**. No Temporal cluster is
deployed in this codebase (no `temporalio` dependency, confirmed) -- Phase 1 has no long-running
orchestration need beyond what a synchronous Mutation Gateway command already satisfies. This is a
construction standard + a small library (`identity.py`, `retry_policy.py`, `signals.py`) a future
Temporal integration must use, exactly the same "mechanism present, infra feed deferred" shape as
Document 66's zero-trust functions and Document 70's replica routing.

| TMP-FR | Requirement | Where enforced / evidenced |
|---|---|---|
| TMP-FR-001 | Temporal role (orchestration only) | Architectural invariant (CLAUDE.md §2 AG-10); no workflow engine exists to violate it yet. |
| TMP-FR-002 | Workflow identity | `identity.py::derive_workflow_id()` -- `{namespace}.{workflow_type}.{business_id}`, rejects non-identifier-safe input. |
| TMP-FR-003 | Deterministic workflow / external calls only in Activities | Structural: the only way to reach GxP state is `services/gxp-api`'s command handlers, which already require `evaluate_policy` + a DB transaction -- a hypothetical Activity would call the exact same HTTP surface every other caller uses. |
| TMP-FR-004 | Activity idempotency | Already satisfied by construction: every state-changing GxP command requires `idempotency_key` (MUT-FR-010, `check_idempotency()`); a Temporal Activity is just another caller of that same contract. |
| TMP-FR-005 | Workflow versioning | No workflow code exists to version yet; policy recorded here for when it does. |
| TMP-FR-006 | No regulatory truth in Temporal | AG-10: `audit.audit_events` (Document 05) is the only regulated ledger; a future Temporal history is explicitly non-authoritative. |
| TMP-FR-007 | Domain command via GxP API | Structural, same as TMP-FR-003 -- there is no other write path. |
| TMP-FR-008 | Signals persist authoritative decision first | Policy: a workflow signal must be preceded by (or itself trigger) a real Mutation Gateway command, never a workflow-only state change. |
| TMP-FR-009 | Queries are operational view only | Policy; regulated UI already reads authoritative detail via each module's own GET endpoints, never a workflow query. |
| TMP-FR-010 | Timers vs domain due-date source | Policy: any future timer's `due_at` is read from the owning domain record (e.g. a QMS due date), never invented in workflow code. |
| TMP-FR-011 | Retry policy by error class | `retry_policy.py::classify_retry()` -- a compliance-critical dependency failure (503/500, or a transient 409 race) is retryable; a settled business/authorization/validation/signature outcome is not. |
| TMP-FR-012 | Timeouts per activity | Configuration policy for a future worker; no activity code exists yet. |
| TMP-FR-013 | Heartbeats | Configuration policy for a future long-running activity; none exists yet. |
| TMP-FR-014 | Cancellation maps to domain cancellation | Policy: a workflow cancellation must call the domain's own cancel/hold command (e.g. `qms_deviation.close`), never silently abandon a regulated process. |
| TMP-FR-015 | Compensation is a new domain transaction | Policy, directly inherited from AG-08: compensation calls the owning module's own command (a new audit event), never edits/rolls back history. |
| TMP-FR-016 | Human task authority lives in domain/QMS record | Already true: every QMS task (deviation, CAPA, NCR, change control) has its own authoritative state machine in `app/modules/qms/*`; nothing waits on Temporal for authority. |
| TMP-FR-017 | Child workflows for bounded subprocesses | Design guidance for a future worker; not applicable without workflow code. |
| TMP-FR-018 | Continue-as-new preserves business identity | Design guidance; `derive_workflow_id()`'s scheme is exactly what a continued run must keep. |
| TMP-FR-019 | Namespace isolation | `identity.py::derive_workflow_id()`'s `namespace` parameter; ADR-0006 single-tenant-per-deployment applies the same way. |
| TMP-FR-020 | Worker identity scopes | Deployment concern for a future worker process; would use the same non-human service-identity pattern `app/modules/security/identity_*` already establishes. |
| TMP-FR-021 | Task queues | Deployment concern; not applicable without a worker. |
| TMP-FR-022 | Temporal HA | Deployment/DR concern (Document 76), not application-code testable here. |
| TMP-FR-023 | Temporal outage | Policy: existing GxP records stay valid (they don't depend on Temporal for their own consistency); new orchestration would pause, not existing regulated data. |
| TMP-FR-024 | GxP DB outage -- never invent success | `retry_policy.py::classify_retry()` routes a `DEPENDENCY_UNAVAILABLE`/`PRIMARY_UNAVAILABLE` failure to retry, never to a synthesized success; `app/main.py`'s `OperationalError` handler already fails closed with `DEPENDENCY_UNAVAILABLE` for the same reason. |
| TMP-FR-025 | Visibility, not a regulated source | Policy for a future ops UI; the actual regulated status is always each module's own GET endpoint. |
| TMP-FR-026 | Audit linkage (correlation IDs) | Already true: every audit event and outbox event carries `correlation_id`/`causation_id` (MUT-FR-027); a future workflow ID is just one more correlation value on the same commands. |
| TMP-FR-027 | Temporal Web/admin security | Deployment concern (Document 66/77), not applicable without a deployed Temporal cluster. |
| TMP-FR-028 | Data minimization in workflow payloads | Policy: a future workflow payload carries entity IDs/refs, never evidence bytes -- consistent with Document 72's evidence-by-reference design already in place. |
| TMP-FR-029 | Temporal backup/restore | Deployment/DR concern (Document 76); orchestration continuity only, never a GxP data recovery path. |
| TMP-FR-030 | Replay/time-skip/version-compatibility testing | Mandatory once workflow code exists; `identity.py`/`retry_policy.py` are unit-tested now (`tests/test_workflowops.py`) as the reusable primitives those future workflow tests will exercise. |

## Known limitation

No Temporal cluster or `temporalio` worker exists in this codebase. Every TMP-FR above that requires
live workflow code (versioning, timers, heartbeats, child workflows, continue-as-new, replay tests) is
deferred until a real orchestration need is validated -- Phase 1's regulated flows are fully served by
synchronous Mutation Gateway commands, matching CLAUDE.md's own note that Temporal is orchestration
only, never regulatory truth, and is not required for the platform to function.
