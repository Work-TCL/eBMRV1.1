# ADR-0004-REQUIREMENT-ID-NAMESPACE — Requirement-ID namespace remediation

**Status:** Accepted  
**Date:** 2026-08-21  
**Deciders:** Platform Architect, Specification Owner

---

## Context

`DRV-FR` was used by Documents 44 and 91; `DEP-FR` by Documents 77 and 104 (SG-001, SG-002).

## Decision

Document 91 → `DRQ-FR`; Document 104 → `DPM-FR`. Aliases retained for one revision. A CI conformance check
enforces global requirement-ID uniqueness and single event producers.

## Rationale

An identifier must resolve to exactly one requirement for traceability, test credit and change impact.

## Consequences

Patches P-01 and P-02 in `gap-resolution/patches/DOCUMENT_PATCH_LIST.md` must be applied through document
change control; traceability artefacts are regenerated afterwards.
