# eBMR / eDHR Specification Authoring Standard
## Implementation-Ready Module Specification Standard — v1.0

This standard applies to Documents 03–105 and any child specification.

A specification must be detailed enough for Codex/Claude Code to implement with minimal interpretation.

Every module specification must contain, where applicable:

1. Objective and non-goals
2. Scope and exclusions
3. Dependencies and assumptions
4. Terminology
5. Actors/personas/roles
6. Module architecture and boundaries
7. All functionalities and sub-functionalities
8. State machines/workflows
9. Business rules
10. Authorization/RBAC/SoD
11. Electronic-signature behavior
12. Audit behavior
13. Entities/data model
14. Fields, data types, relationships
15. Database ownership
16. Suggested tables, indexes, constraints and concurrency controls
17. APIs and versioning
18. Request/response examples
19. Stable error codes
20. Idempotency/replay behavior
21. Events/outbox contracts
22. External integrations
23. UI screens/forms/actions
24. Validations
25. Calculations/precision/rounding
26. Failure/recovery behavior
27. Security controls
28. Configuration model
29. Observability/alerts
30. Retention/archive
31. Migration/upgrade behavior
32. Performance/scaling
33. Repository/module/file structure
34. Implementation sequence/tasks
35. Acceptance criteria
36. Positive/negative/concurrency/failure test cases
37. Validation/traceability IDs
38. Explicit Codex/Claude Code prohibited/required behaviors

If an item is not applicable, say why. Do not silently omit it.

## Coding-Agent Rule

Where the specification does not define a decision that affects regulated behavior, the coding agent must not guess. It must raise the missing decision as a specification gap.

High-level prose such as “support CAPA” or “implement audit” is never sufficient without sub-functionalities, state, data, rules and tests.
