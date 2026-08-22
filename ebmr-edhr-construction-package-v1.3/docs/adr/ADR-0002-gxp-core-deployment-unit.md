# ADR-0002-GXP-CORE-DEPLOYMENT-UNIT — GxP Core deployed as a modular monolith

**Status:** Accepted  
**Date:** 2026-08-21  
**Deciders:** Platform Architect, Specification Owner

---

## Context

Document 02 §11 lists 19 logical services and states that deployment units may be consolidated.

## Decision

Deploy GxP Core as one service (`services/gxp-api`) containing enforced module boundaries; Temporal
workers, platform, security, integration and AI run as separate services.

## Rationale

The regulated transaction requires domain state, record version, audit and outbox to commit atomically in
one PostgreSQL transaction (MUT-FR-015). Splitting those across network boundaries would force distributed
transactions, which Document 02 §13.1 prohibits.

## Consequences

Module boundaries are enforced by static guardrails (no cross-module repository imports). Extraction of a
module into its own service is possible only where it does not participate in the regulated transaction.
