# ADR-0005-FRAPPE-BASE-LAYER-ERPNEXT-EXTERNAL — Frappe Framework is the base layer; ERPNext is external only

**Status:** Accepted  
**Date:** 2026-08-21  
**Deciders:** Platform Architect, Specification Owner

---

## Context

Document 01 names **Frappe Framework** as the recommended foundation and Document 02 §5 states
"**Primary Application Framework:** Frappe Framework". ERPNext appears in the baseline only as one of
several external ERP systems (alongside SAP S/4HANA, Oracle Fusion and Dynamics 365) reached through an
adapter: Document 48 defines the provider contract, Document 49 the ERPNext adapter, and both require
public/supported APIs rather than direct ERPNext database writes. Document 48 additionally prohibits
importing SAP/Oracle/Dynamics/ERPNext SDK types into GxP domain packages.

The baseline states this positively but never negatively. Because an ERPNext adapter specification exists,
an implementer could reasonably assume ERPNext is installed as part of the platform. It is not.

## Decision

1. **Frappe Framework is the base layer.** The platform is a custom Frappe app (`apps/ebmr_frappe`)
   running on Frappe, with the proprietary GxP Core as an independent service tier.
2. **ERPNext is never installed into the platform runtime.** It is an optional *external* system that a
   customer may already operate, integrated exactly like SAP, Oracle or Dynamics.
3. **Frappe is a pinned external dependency, not vendored.** Frappe core is never copied into the
   monorepo, which is what makes guardrail AG-01 mechanically enforceable: core files are not in the tree,
   so they cannot be edited.
4. Where a needed capability exists in ERPNext (stock, purchasing, accounting), the platform either owns
   it as regulated GxP state or integrates to the customer's ERP per Document 48's ownership matrix. It
   does not adopt ERPNext doctypes as its own model.

## Rationale

ERPNext carries commercial/financial semantics and its own record lifecycle. Adopting it as a base layer
would put commercially-owned doctypes inside the regulated boundary, breaking the single-authoritative-
owner rule (AG-05) and the Document 48 ownership matrix, and would make ERPNext upgrades a validated-state
change for regulated records.

## Consequences

- Development environments install Frappe (bench or container) plus the custom app. ERPNext, if present at
  all, runs as a separate instance for adapter testing.
- `guardrails` fail on any ERPNext import inside `services/gxp-api` or `packages/`.
- Removing ERPNext from a deployment must not affect any regulated function.
