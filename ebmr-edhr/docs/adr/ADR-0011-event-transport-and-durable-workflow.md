# ADR-0011-EVENT-TRANSPORT-AND-DURABLE-WORKFLOW — NATS/JetStream and Temporal to be built; current stand-ins are interim only

**Status:** Accepted
**Date:** 2026-09-09
**Deciders:** Project Owner (via Claude Code session), Platform Architect

---

## Context

Two architecture non-negotiables depend on infrastructure that is not built:

- **AG-09 / Document 73 (SPEC-DATA-005, EVT-FR-001…030):** the PostgreSQL transactional outbox is the
  authoritative event source and **NATS/JetStream is the transport**. Today `services/gxp-api` runs an
  in-process `asyncio` loop (`app/main.py::outbox_publisher_loop`) that claims committed outbox rows
  under `SKIP LOCKED` and calls a **stand-in publisher** (`app/modules/eventbus/outbox.py`) — no broker,
  no durable stream, no cross-service delivery, no consumer replay by `event_id`.
- **AG-10 / Document 74 (SPEC-DATA-006, TMP-FR-001…030):** **Temporal** orchestrates durable workflows.
  Today there is a `workflowops` stand-in module and no Temporal runtime. Requirements that name Temporal
  explicitly (batch-execution recovery/restart clauses, SG-047/048 sub-items, TEST-FR-010 workflow
  replay/version tests) cannot be satisfied or tested.

The transactional-outbox *pattern* (write the event in the same transaction as the domain state; publish
only after commit) is implemented correctly and is the part that carries the regulated guarantee. What is
missing is the transport and the durable-workflow engine.

The Project Owner was asked whether to formally descope both for a single-customer deployment, build
both, or build NATS only. The decision is **build both**.

## Decision

1. **NATS/JetStream and Temporal are in scope and will be implemented.** The baseline is honoured as
   written; there is no descoping SPEC_GAP.

2. **The current in-process outbox publisher and `workflowops` stand-in are recorded as an interim
   implementation state, not the target architecture.** Until the real infrastructure lands:
   - the validation package **must not claim** NATS/JetStream or Temporal exist;
   - any module whose `CODE_COMPLETE` evidence depends on durable transport or Temporal orchestration
     stays below `CODE_COMPLETE` for those requirements;
   - **SG-183** tracks this interim state and its closure criteria.

3. **Both land in WP-11 (Data / Infrastructure / DR / SRE).** Ordering:
   - **NATS/JetStream first** — replace the stand-in publisher with a JetStream producer (durable
     stream, publish-ack before `mark_outbox_published`, subject convention per Document 73), stand up
     at-least-once consumers for projections and integrations, add the EVT/TEST contract tests
     (duplicate, replay by `event_id`, out-of-order, poison event).
   - **Temporal second** — deploy the runtime, move `workflowops` and the batch-execution
     recovery/escalation paths onto Temporal workflows/activities, add deterministic replay + time-skip
     tests (TEST-FR-010), keep authoritative state re-read from the owning service (AG-10 — no regulated
     truth in workflow variables).

4. **Contract-first still applies (Document 73/101/113).** The AsyncAPI subject/stream contracts are
   committed before the JetStream producer is wired — this also unblocks the event half of **SG-013**
   for the non-QMS modules that currently have no committed event schema.

## Rationale

The platform's value case includes multi-service projection and integration delivery and durable
recovery of long-running batch/QMS workflows; a single-customer deployment does not remove those
requirements, it only defers when they bite. Recording the stand-ins as interim (rather than as an
accepted permanent architecture) keeps the validation package honest and gives every dependent SPEC_GAP a
single closure reference.

## Consequences

- WP-11 scope explicitly includes NATS/JetStream and Temporal delivery; `status/build-status.json` WP-11
  requirement rows for DATA-FR-014, EVT-FR-002/003/004 and TMP-FR-* are re-opened from any prior
  stand-in-based "verified" claim.
- **SG-183** opens. **SG-013**'s event half references the AsyncAPI contract work here.
  **SG-166** (NATS/cache numeric baselines) is a dependency of the NATS work.
- Dependencies added for NATS and Temporal clients require Document 104 justification entries
  (`docs/generated/40_SBOM_LICENSE_DEPENDENCY_REGISTER.md`) before merge.
- `app/main.py::outbox_publisher_loop` and `app/modules/eventbus/outbox.py` carry a header comment
  pointing at this ADR and SG-183 so they are not mistaken for the finished implementation.
- Deferred until this lands: TEST-FR-010 (workflow replay), the durable-stream half of TEST-FR-008,
  cross-service consumer contract tests (TEST-FR-007).
