# ADR-0001-REPOSITORY-LAYOUT — Repository layout reconciled to spec-declared paths

**Status:** Accepted  
**Date:** 2026-08-21  
**Deciders:** Platform Architect, Specification Owner

---

## Context

The Project Construction Instruction sketches a generic skeleton (`services/mutation-gateway`,
`services/signature-service`, …). The controlled specifications repeatedly declare concrete paths:
`services/gxp-api/src/modules/...`, `services/workers/`, `services/platform/`, `services/security/`,
`apps/ebmr_frappe/...`, `contracts/events/`, `packages/data-contracts/`, `edge/gateway/`,
`connectors/lims/`, `validation/requirements/`, `tests/infrastructure/`, `docs/runbooks/`.

## Decision

Follow the specification-declared paths. GxP Core logical services (Document 02 §11) become **modules**
inside `services/gxp-api`, not separate deployment units. Logical boundaries remain mandatory.

## Rationale

Source precedence places numbered specifications (3) above the Project Construction Instruction (5).
Fifty documents reference `services/gxp-api` paths; renaming them would break every declared file map.

## Consequences

`docs/generated/17_REPOSITORY_STRUCTURE.md` is authoritative for layout. Splitting a module into its own
deployment unit later is an infrastructure change, not a code restructure, because boundaries are enforced
by guardrails from day one.
