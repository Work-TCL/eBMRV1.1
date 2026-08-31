# ADR-0003-CONTRACT-FIRST-CODEGEN — Contract-first generation of types

**Status:** Accepted  
**Date:** 2026-08-21  
**Deciders:** Platform Architect, Specification Owner

---

## Context

497 API operations and 484 event types are declared by name; field-level schemas were missing (SG-013).

## Decision

Author OpenAPI/AsyncAPI/JSON Schema per work package before implementation, and generate TypeScript types
from the contracts into `packages/data-contracts`. Code never generates the contract.

## Rationale

Prevents silent breaking changes to validated interfaces and makes the compatibility registry meaningful.

## Consequences

CI rejects an implementation without a committed schema. Contract review is a distinct approval step.
