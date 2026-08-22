# US eBMR / eDHR Regulated Manufacturing Platform
## Document 110 — Calculation Precision, Rounding, UOM & Numeric Integrity Baseline — v1.0 APPROVED

**Specification ID:** SPEC-GXP-008
**Status:** APPROVED v1.0 (construction baseline) — approvers of record: Head of Quality and Product Owner
**Closes:** SG-007
**Approval:** Approved by the Project Owner during construction review on 2026-08-21. A formal Part 11 signature record must be captured in the QMS against this version before validated release; the approval block below is the record of the construction decision.

**Primary Dependencies:** Document 08 (Rules & Calculation Engine), Document 17 (Yield/Reconciliation), Document 21 (Dispensing/Weighing), Document 23 (QC), Document 97 (Coding Standards), Document 01 C-015 (Unit of Measure)

---

# 0. Why this document exists

Document 08 requires rounding mode, stage and decimal places to be explicit and versioned. Document 17 requires yield calculations to be reproducible. Document 97 mandates decimal arithmetic and prohibits binary floating point for regulated values. None of them fixes the **default numeric policy per calculation class**. Rounding stage alone can change whether a batch passes a limit, so this is a regulated decision, not an implementation detail.

# 1. Principles

| # | Principle | Consequence |
|---|---|---|
| N1 | All regulated quantities use exact decimal arithmetic. Binary floating point is prohibited end to end (service, database, contract, UI). | `numeric` in PostgreSQL, decimal library in TypeScript, string transport in JSON. |
| N2 | Rounding happens at **declared stages only**: at capture (to instrument resolution), at declared intermediate checkpoints, and at presentation. Never silently mid-chain. | Chain is reproducible from raw values. |
| N3 | The raw captured value is always retained alongside any rounded value. | Inspection can recompute. |
| N4 | Comparison against a limit uses the **policy-declared comparison precision**, and the policy states whether the limit is inclusive. | Removes "is 99.4999 within ≥99.5?" ambiguity. |
| N5 | Every calculation result stores the **rule version, policy version and input references** used to produce it. | Reproducibility (Doc 08). |
| N6 | UOM conversion uses controlled conversion factors with declared precision; textual units are prohibited. | Doc 01 C-015. |
| N7 | The same value renders identically in UI, API, export and PDF. | No presentation-layer arithmetic. |

# 2. Calculation classes and default policy (PROPOSED)

| Class | Examples | Storage precision | Rounding mode | Rounding stage | Comparison rule |
|---|---|---|---|---|---|
| CC-1 Mass/weight capture | dispensing, fill weight | instrument resolution, stored as captured (min 4 dp) | none at capture | capture only | compare at instrument resolution |
| CC-2 Volume capture | fill volume, buffer volume | as captured (min 4 dp) | none at capture | capture only | as captured |
| CC-3 Tolerance evaluation | dispense within ±x %, fill weight IPC | 6 dp intermediate | half-up | at comparison only | policy states inclusive/exclusive bounds |
| CC-4 Yield / reconciliation | % yield, theoretical vs actual, line loss | 6 dp intermediate, 2 dp reported | half-up | at each declared reconciliation checkpoint and at presentation | limit inclusive unless stated |
| CC-5 Concentration / potency | assay, potency, strength | 6 dp intermediate, source-specified reported dp | half-up | at reported precision | per specification method |
| CC-6 Count / units | units filled, rejects, samples | integer | n/a | n/a | exact equality |
| CC-7 Time / duration | hold time, filtration time, cycle time | seconds (UTC-based) | none | n/a | inclusive of declared boundary |
| CC-8 Environmental | particle counts, temperature, differential pressure | source resolution | none at capture | comparison only | per method/limit definition |
| CC-9 Statistical / trending | rates, means, control limits | 6 dp internal, 4 dp reported | half-even (banker's) for statistical aggregation | at report generation | advisory only; never a release decision by itself |
| CC-10 Financial/commercial | ERP-facing quantities and values | per ERP contract | per ERP contract | at integration boundary | not a GxP decision path |

**Half-up** is chosen for regulated pass/fail arithmetic because it is the conventional, explainable rule for measurement rounding. **Half-even** is used only for statistical aggregation, where bias avoidance matters and no single result is a release decision.

# 3. UOM model

```text
uom(code, dimension, base_unit, factor numeric(38,18), offset numeric(38,18), precision_dp, status, version)
uom_conversion(from_code, to_code, factor numeric(38,18), rounding_stage, version, effective_from)
```
Rules: conversions are released, versioned data; a batch binds the UOM version in force at issue; conversion never occurs implicitly in a query, a projection or the UI.

# 4. Functional requirements

| ID | Requirement | Detailed behaviour | Acceptance intent |
|---|---|---|---|
| CALC-FR-001 | Decimal end to end | No regulated numeric value passes through a binary float in any layer. | Static check + contract test. |
| CALC-FR-002 | Raw value retention | Every rounded or converted value stores its raw source value and the transformation applied. | Recomputation test. |
| CALC-FR-003 | Declared stages | Rounding occurs only at capture, declared checkpoints and presentation. | Chain reproducibility test. |
| CALC-FR-004 | Versioned policy | Precision/rounding policy is released, versioned configuration bound to the record. | Historic recomputation matches. |
| CALC-FR-005 | Comparison semantics | Limit comparisons state precision and inclusivity explicitly. | Boundary tests pass. |
| CALC-FR-006 | UOM control | Only released UOM codes and conversions are accepted; free-text units rejected. | Negative test. |
| CALC-FR-007 | Cross-surface identity | UI, API, export and PDF render the same value identically. | Render comparison test. |
| CALC-FR-008 | Result provenance | Every calculated regulated value stores rule version, policy version and input record references. | Provenance query. |
| CALC-FR-009 | Instrument resolution | Captured values respect the device's declared resolution; over-precision is not fabricated. | Edge/peripheral test (Doc 46). |
| CALC-FR-010 | Division/zero handling | Division by zero and undefined results produce a typed error, never a silent zero or NaN. | Negative test. |
| CALC-FR-011 | Aggregation order independence | Reconciliation totals are order-independent and reproducible. | Property test. |
| CALC-FR-012 | Change impact | Changing a class policy is a controlled change with revalidation assessment. | Doc 96 trigger recorded. |

# 5. Stable error codes

`UOM_UNKNOWN`, `UOM_CONVERSION_UNAVAILABLE`, `PRECISION_POLICY_UNRESOLVED`, `PRECISION_POLICY_VERSION_MISMATCH`,
`NUMERIC_OVERFLOW`, `DIVISION_UNDEFINED`, `RAW_VALUE_MISSING`, `INSTRUMENT_RESOLUTION_EXCEEDED`.

# 6. Test catalogue

1. Boundary tests at every limit for each calculation class (just inside, exactly at, just outside).
2. Rounding-stage test: value that passes when rounded early and fails when rounded correctly → must fail.
3. Recomputation: historic record recomputes to the identical result using its bound policy version.
4. Float contamination test: any float in the regulated numeric path fails the build.
5. UOM conversion round-trip precision test.
6. Free-text unit rejected.
7. Cross-surface rendering identity (UI vs API vs PDF vs export).
8. Division by zero produces a typed error.
9. Order-independence property test for reconciliation aggregation.
10. Instrument over-precision rejected at capture.

# 7. Validation impact

Calculation correctness is Part 11 and predicate-rule critical (§211.103, §211.188 yield calculations). OQ evidence per Document 84 and rules-engine qualification per Document 82. Any policy change is a revalidation trigger.

# 8. Acceptance criteria

1. Decimal-only numeric path proven by static and runtime checks.
2. Every calculation class has a released policy version.
3. All boundary and recomputation tests pass.
4. A historic batch recomputes identically after a later policy change.

# 9. Claude Code / Codex prohibitions

- Do not use `number`, `float`, `double` or `REAL` for a regulated quantity.
- Do not round in a repository, a projection, a query or a template.
- Do not implement a conversion factor as a literal in code.
- Do not adjust a rounding rule to make a test pass.

# 10. Approval block

| Role | Name | Decision | Date | Signature reference |
|---|---|---|---|---|
| Head of Quality |  |  |  |  |
| Product Owner |  |  |  |  |
