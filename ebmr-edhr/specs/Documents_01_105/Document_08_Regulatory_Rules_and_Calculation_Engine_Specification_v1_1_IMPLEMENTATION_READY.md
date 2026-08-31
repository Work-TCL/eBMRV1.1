# US eBMR / eDHR Regulated Manufacturing Platform
## Document 08 — Regulatory Rules & Calculation Engine — Detailed Functional & Technical Specification — v1.1

**Specification ID:** SPEC-GXP-006  
**Parent Documents:** Document 01 v1.1 (FROZEN) and Document 02 v1.0  
**Dependencies:** Documents 01–07; Recipe/Batch/Material/QC/Release specifications  
**Status:** Proposed v1.1 — IMPLEMENTATION-READY BASELINE / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products  
**Future Profiles:** Medical Devices and Pharmaceuticals  
**Date:** 2026-08-20

---

# 1. Objective

Define a deterministic, version-controlled engine for regulatory/manufacturing decisions and calculations without allowing customers or developers to inject uncontrolled executable code.

# 2. Rule Categories

```text
RULE ENGINE
├── Eligibility
│   ├ Material
│   ├ Equipment
│   ├ Personnel
│   └ Area/Product
├── Progression / Sequence
├── Limits & Acceptance
├── Calculations
│   ├ Yield
│   ├ Potency
│   ├ Conversion
│   └ Reconciliation
├── Signature Requirements
├── Exception / Deviation Triggers
├── Time Windows
└── Release Eligibility
```

# 3. Architecture

```text
Released Rule Definition
        ↓ compile/validate
Constrained Rule Runtime
        ↓
Typed Inputs + Source Metadata
        ↓
Deterministic Evaluation
        ↓
Result:
  PASS / FAIL / HOLD / N/A
  + calculated values
  + reason codes
  + rule/version
        ↓
Mutation Gateway / Execution / Release
        ↓
Audit + persisted evaluation reference
```

# 4. Detailed Requirements

| ID | Requirement | Detailed behavior / sub-functionalities | Acceptance intent |
|---|---|---|---|
| RUL-FR-001 | Controlled rule object | Every GxP-critical rule/formula has stable ID, type, semantic version, status, scope and owner. | Rule identifiable in historical decision. |
| RUL-FR-002 | Rule lifecycle | Draft → Review → Approved/Released → Effective → Superseded/Retired. Released version immutable. | No in-place formula edit. |
| RUL-FR-003 | Effective dating | Rule version has effective-from/to and profile/site/product applicability; execution snapshots exact eligible version. | Future/obsolete rule not selected. |
| RUL-FR-004 | Deterministic evaluation | Same inputs + same released rule version produce same result, independent of UI/server instance. | Golden tests deterministic. |
| RUL-FR-005 | Safe expression language | GxP formulas/rules use constrained DSL/AST/function catalogue; arbitrary Python/JavaScript/SQL/network/file execution prohibited. | Expression cannot execute arbitrary code. |
| RUL-FR-006 | Typed inputs | Inputs define data type, unit, required/optional, precision, acceptable null behavior and source. | Wrong unit/type rejected. |
| RUL-FR-007 | Typed outputs | Outputs define result type, unit, precision, status/reason codes and downstream action. | Consumers contract stable. |
| RUL-FR-008 | Unit management | Use canonical UOM IDs and validated conversions; dimensional incompatibility rejected. | kg cannot be silently compared to L. |
| RUL-FR-009 | Decimal arithmetic | Use deterministic decimal arithmetic for regulated calculations; avoid binary floating-point where it could alter results. | Precision tests pass. |
| RUL-FR-010 | Rounding rules | Formula defines rounding mode, stage and decimal places/significant figures. | Rounding is explicit/versioned. |
| RUL-FR-011 | Limit rules | Support inclusive/exclusive min/max, target/tolerance, enumerations, ranges and conditional limits. | Boundary tests included. |
| RUL-FR-012 | Eligibility rules | Material, equipment, operator, area, recipe and constituent eligibility rules evaluate before relevant action. | Ineligible resource blocks. |
| RUL-FR-013 | Sequence/progression rules | Define prerequisite steps, parallel joins, conditional branches, hold points and permitted progression. | Out-of-sequence command denied. |
| RUL-FR-014 | Signature rules | Determine required signature meaning, signer role/qualification, independence and count/order. | Signature policy version captured. |
| RUL-FR-015 | Deviation/exception triggers | Out-of-limit, expired status, manual override, timing breach, environment excursion or missing evidence can generate configured exception/hold. | Trigger result deterministic. |
| RUL-FR-016 | Release rules | Aggregate required completion/QC/QMS/reconciliation/signature/equipment/environment evidence into release eligibility result with blockers. | Release reason codes explainable. |
| RUL-FR-017 | Yield calculation | Support theoretical/actual/stage yield and percentage according to released formula, input sources, verification policy and rounding. | §211.103-type scenarios testable where applicable. |
| RUL-FR-018 | Potency/assay adjustment | Support controlled potency correction with exact assay source/version, formula, units and precision. | Material quantity traceable. |
| RUL-FR-019 | Reconciliation calculation | Issued/dispensed/consumed/returned/rejected/destroyed quantities reconcile according to released rule/tolerance. | Variance creates blocker/event. |
| RUL-FR-020 | Time-window rules | Support process hold times, expiry/retest, calibration due, training expiry, timer limits and environmental windows using authoritative time. | Boundary/timezone tests pass. |
| RUL-FR-021 | Decision explanation | Every evaluation returns rule ID/version, inputs/reference IDs, outcome, reason codes and relevant calculated values. | QA can explain decision. |
| RUL-FR-022 | Evaluation persistence | Persist critical evaluation result/reference with regulated mutation/audit; avoid relying on recomputation under a newer rule. | Historical result reproducible. |
| RUL-FR-023 | Simulation/test mode | Authorized users can simulate draft rules against test/historical sanitized data without affecting regulated state. | Simulation clearly non-production. |
| RUL-FR-024 | Rule test cases | Each released critical rule includes approved positive, boundary, negative and error test vectors. | No release without tests. |
| RUL-FR-025 | Independent verification | Critical formulas can require independent reviewer approval/test evidence before release. | Formula author cannot self-approve if policy says no. |
| RUL-FR-026 | Change impact | Changing rule/formula triggers impact assessment for products, recipes, batches, tests, validation and customer configuration. | Affected scope report generated. |
| RUL-FR-027 | Snapshot binding | Batch/record snapshots reference exact rule/calculation versions required for execution. | Mid-batch rule change does not alter history. |
| RUL-FR-028 | External result rules | LIMS/ERP/Edge values are validated against source mapping, unit, schema and quality before rule evaluation. | Bad source data fails/quarantines. |
| RUL-FR-029 | Missing/invalid inputs | Rule defines explicit behavior: fail, hold, not-applicable or exception; never silently substitute default for critical missing data unless released rule permits. | Missing critical input cannot pass. |
| RUL-FR-030 | Overflow/domain errors | Divide-by-zero, invalid logarithm/range, overflow, unit mismatch or invalid enum produce controlled failure with no fabricated result. | Calculation errors observable. |
| RUL-FR-031 | Rule engine versioning | Record engine/runtime version separately from business rule version; engine upgrade requires regression. | Same rule under new engine validated. |
| RUL-FR-032 | Performance/cache safety | Caching compiled rules is allowed only if cache key includes immutable rule version and tenant/profile; cache cannot alter deterministic outcome. | No stale rule execution. |

# 5. Rule Object

```text
rule_id
rule_type
semantic_version
schema_version
scope
status
effective_from/to
expression/AST
input_contract[]
output_contract
unit_policy
precision_policy
rounding_policy
reason_codes[]
test_vectors[]
author
reviewers/signatures
released_at
engine_compatibility
```

# 6. Example Calculation Object

```json
{
  "rule_id":"CALC-YIELD-001",
  "version":"2.1.0",
  "inputs":[
    {"name":"actual_qty","type":"decimal","uom":"kg"},
    {"name":"theoretical_qty","type":"decimal","uom":"kg"}
  ],
  "output":{"name":"yield_pct","type":"decimal","uom":"%","scale":2},
  "rounding":{"mode":"HALF_UP","stage":"FINAL","scale":2},
  "expression":"(actual_qty / theoretical_qty) * 100"
}
```

Production implementation should use parsed/validated AST or controlled function model rather than `eval`.

# 7. Safe Function Catalogue

Initially permit explicitly reviewed functions such as:
- decimal arithmetic;
- comparisons;
- min/max;
- controlled rounding;
- unit conversion;
- conditional expression;
- date/time difference against authoritative UTC;
- set membership;
- boolean logic.

Prohibit:
- file/network I/O;
- DB queries from expression;
- shell/process execution;
- dynamic imports;
- reflection;
- random values;
- current browser time;
- unbounded loops.

Data retrieval occurs in domain services before evaluation and is supplied as typed inputs.

# 8. Release Eligibility Result

Example:

```json
{
  "eligible": false,
  "rule_set_version":"DDCP-RELEASE-4.2",
  "blockers":[
    {"code":"OOS_OPEN","record_id":"OOS-18"},
    {"code":"MATERIAL_RECONCILIATION_FAILED","variance":"0.8%"}
  ],
  "warnings":[],
  "evaluated_at":"...UTC..."
}
```

Final QA release still requires authorized electronic signature; rules do not replace Quality authority.

# 9. Validation Strategy

Each critical formula/rule:
- intended purpose;
- input/output contract;
- risk class;
- test vectors;
- boundary values;
- invalid inputs;
- unit tests;
- independent review where required;
- release signature;
- regression on engine upgrade.

# 10. Predicate-Rule Examples

For applicable drug/DDCP profiles, the engine can support:
- controlled yield determination/verification;
- component weighing/verification;
- recording significant batch parameters;
- automated equipment checks.

Exact applicability belongs to product/profile compliance matrices, not this generic engine.

# 11. Failure Behavior

- missing critical input → fail/hold per released rule;
- invalid unit → reject;
- divide by zero/domain error → controlled calculation failure;
- unreleased rule → cannot execute production;
- rule engine unavailable → dependent regulated action fails closed;
- rule version not found for historical snapshot → integrity incident; no substitution with latest.

# 12. Validation Tests

- deterministic repeat;
- decimal precision;
- every rounding mode used;
- min/max boundary;
- unit conversion;
- invalid unit;
- missing input;
- null behavior;
- effective dates;
- superseded rule snapshot;
- yield;
- potency;
- reconciliation;
- time-window;
- signature policy;
- release blocker aggregation;
- cache stale-rule test;
- engine upgrade replay/golden tests.

# 13. Acceptance Gate

Freeze requires:
- constrained DSL/AST decision;
- decimal/UOM libraries selected and license-reviewed;
- canonical calculation test-vector format;
- initial V1 DDCP rule catalogue;
- Release Engine interface;
- change-control/validation workflow.

# 14. Developer / AI-Agent Rules

Never use `eval`, arbitrary Python or arbitrary JavaScript for regulated formulas.
Never silently coerce incompatible units.
Never use floating-point arithmetic where validated decimal result is required.
Never replace missing input with zero/default unless the released rule explicitly defines it.
Never apply “latest” rule to an already-issued batch; use snapshot-bound version.

# Regulatory Source Basis

This specification is an engineering/control design document. Regulatory applicability remains dependent on intended use, predicate-rule records, product profile, and customer procedures.

Primary current sources used for the GxP Core baseline:

1. **21 CFR Part 11 — Electronic Records; Electronic Signatures**
   - §11.10 Controls for closed systems
   - §11.50 Signature manifestations
   - §11.70 Signature/record linking
   - §11.100 General requirements
   - §11.200 Electronic signature components and controls
   - §11.300 Controls for identification codes/passwords
2. **FDA — Part 11, Electronic Records; Electronic Signatures — Scope and Application**
3. Applicable predicate-rule requirements, including drug CGMP / device QMSR / combination-product controls.
4. For regulated calculations and batch evidence, applicable provisions may include 21 CFR §§211.68, 211.101, 211.103 and 211.188.

Reference URLs:
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11
- https://www.fda.gov/regulatory-information/search-fda-guidance-documents/part-11-electronic-records-electronic-signatures-scope-and-application
- https://www.law.cornell.edu/cfr/text/21/11.10
- https://www.law.cornell.edu/cfr/text/21/11.70
- https://www.law.cornell.edu/cfr/text/21/211.68
- https://www.law.cornell.edu/cfr/text/21/211.103
- https://www.law.cornell.edu/cfr/text/21/211.188

**Important:** this product shall be described as *designed to support compliance* and *validation-ready*. It shall not be marketed as automatically “FDA certified” or universally “Part 11 compliant.”


---

# IMPLEMENTATION-GRADE BLUEPRINT

The sections below are normative for implementation. A coding agent shall not invent missing behavior where this specification is explicit. If an implementation question changes regulated behavior, state, authorization, signature, audit, retention or data ownership, implementation must stop and raise a specification issue/change request rather than guessing.

## A. Required Deliverables from the Implementation Team

For this module, the implementation PR/release shall include:

1. application/domain code;
2. database migrations;
3. OpenAPI contract updates;
4. JSON Schema/event contract updates;
5. unit tests;
6. API tests;
7. authorization/negative tests;
8. concurrency/idempotency tests where applicable;
9. failure/recovery tests;
10. audit/signature traceability tests;
11. observability/health instrumentation;
12. configuration defaults;
13. migration/rollback notes;
14. requirement-to-test traceability;
15. SBOM/license impact update;
16. validation-impact note.

## B. Definition of Done

A requirement is not “implemented” merely because a screen exists.

It is complete only when:

- server-side behavior matches the requirement;
- authorization is enforced;
- required audit/signature behavior exists;
- database constraints support the intended invariant;
- APIs and events are versioned;
- expected failures are handled;
- tests prove positive and negative behavior;
- documentation and traceability are updated;
- no prohibited bypass path exists.

## C. Cross-Cutting Engineering Conventions

### Identifiers
- UUIDv7 or another approved sortable unique identifier for internal immutable IDs.
- Human/business numbers may use controlled prefixes/sequences but never replace immutable internal IDs.
- All foreign references use immutable internal IDs.

### Time
- Store authoritative regulated time in UTC.
- Use `timestamptz` in PostgreSQL.
- Local timezone is metadata/presentation only.
- Browser/client time is never authoritative.

### Monetary/quantity/calculation values
- Use decimal/numeric types, never binary float for regulated calculations.
- Store UOM explicitly.
- Precision/scale follows released rule/specification.

### Concurrency
- Use optimistic concurrency via version columns for regulated aggregates.
- Use unique constraints/idempotency for replayable external commands.
- Use row/advisory locks only where resource reservation requires pessimistic control.

### Logging
- Operational logs include request/correlation IDs.
- Do not log credentials, tokens, OTPs, secrets, raw authentication assertions or sensitive payloads unnecessarily.
- GxP audit remains distinct from application logs.

### Database access
- Application runtime uses least-privilege service roles.
- No application feature shall require DBA privileges.
- Direct production SQL changes to regulated records are prohibited outside a controlled incident/change process.

### Testing
Every module shall include:
- happy path;
- authorization denial;
- validation failure;
- stale/concurrent write;
- duplicate/replay where applicable;
- dependency outage;
- restart/recovery;
- data integrity;
- audit verification;
- signature verification where applicable.



# 15. Concrete Package Structure

```text
services/gxp-api/src/modules/rules/
├── rule-registry.service.ts
├── rule-release.service.ts
├── evaluator/
│   ├── parser.ts
│   ├── ast.ts
│   ├── type-checker.ts
│   ├── evaluator.ts
│   └── safe-functions.ts
├── decimal.service.ts
├── uom.service.ts
├── calculation.service.ts
├── explanation.service.ts
├── test-vector.service.ts
└── errors.ts

packages/rule-sdk/
├── schemas/
├── compiler/
└── fixtures/
```

# 16. PostgreSQL Tables

## `gxp_rule_definition`

```text
rule_object_id uuid PK
tenant_id uuid
rule_id varchar(160) NOT NULL
rule_type varchar(60) NOT NULL
semantic_version varchar(40) NOT NULL
schema_version varchar(20) NOT NULL
scope jsonb NOT NULL
status varchar(40) NOT NULL
effective_from timestamptz
effective_to timestamptz
expression_ast jsonb NOT NULL
input_contract jsonb NOT NULL
output_contract jsonb NOT NULL
unit_policy jsonb
precision_policy jsonb
rounding_policy jsonb
reason_codes jsonb
engine_compatibility varchar(80)
released_vault_object_id uuid
```

Unique `(tenant_id, rule_id, semantic_version)`.

## `gxp_rule_evaluation`

Only persist evaluations required for regulated evidence:

```text
evaluation_id uuid PK
tenant_id uuid
rule_object_id uuid NOT NULL
aggregate_type varchar(80)
aggregate_id uuid
aggregate_version bigint
input_hash char(64)
inputs_or_refs jsonb
result jsonb NOT NULL
outcome varchar(40)
evaluated_at timestamptz
engine_version varchar(40)
correlation_id uuid
```

# 17. DSL / AST Design

Recommended V1 expression grammar supports:
- literals;
- typed variables;
- arithmetic;
- comparisons;
- boolean logic;
- `if/then/else`;
- safe functions;
- unit-aware conversion.

Do not support user-defined loops, recursion, network access or DB access.

Example AST:

```json
{
  "op":"multiply",
  "args":[
    {"op":"divide","args":[{"var":"actual"},{"var":"theoretical"}]},
    {"decimal":"100"}
  ]
}
```

# 18. Decimal & UOM Rules

Use a reviewed arbitrary-precision decimal library.
UOM service must:
- have controlled unit catalogue;
- define dimension;
- define conversion factor/offset;
- version conversion rules if business-specific;
- reject incompatible dimensions.

# 19. Rule API

Authoring/query:
- `POST /rules/v1/drafts`
- `POST /rules/v1/{ruleId}/validate`
- `POST /rules/v1/{ruleId}/simulate`
- `POST /rules/v1/{ruleId}/release`
- `GET /rules/v1/{ruleId}/versions`

Runtime internal:
- `POST /rules/v1/evaluate`

Runtime request references released immutable rule version, never “latest”.

# 20. Evaluation Result Contract

```json
{
  "evaluation_id":"...",
  "rule_id":"MAT-ELIG-001",
  "rule_version":"3.0.1",
  "outcome":"FAIL",
  "reason_codes":["MATERIAL_EXPIRED"],
  "calculated_values":{},
  "engine_version":"1.0.0",
  "evaluated_at_utc":"..."
}
```

# 21. Calculation Examples to Implement First

1. theoretical/actual yield;
2. yield percentage;
3. material reconciliation;
4. potency adjustment;
5. target/tolerance check;
6. expiry/retest eligibility;
7. calibration due check;
8. training/qualification expiry;
9. process hold-time;
10. release blocker aggregation.

# 22. Rule Authoring UI

Screens:
- Rule Catalogue
- Rule Draft Editor
- Input/Output Contract
- Units/Precision/Rounding
- Test Vectors
- Simulation
- Review/Approval
- Released Versions
- Impact Analysis

Production users cannot edit released rules.

# 23. Rule Test Vector Format

```json
{
  "test_id":"TV-001",
  "inputs":{"actual":"95.0","theoretical":"100.0"},
  "expected":{
    "outcome":"PASS",
    "yield_pct":"95.00"
  }
}
```

Each released rule has:
- nominal;
- lower boundary;
- upper boundary;
- just below/above boundary;
- invalid type;
- invalid unit;
- null/missing;
- arithmetic error where relevant.

# 24. Engine Upgrade Strategy

Before engine runtime upgrade:
1. replay golden test corpus for all released rule types;
2. compare outputs;
3. document any semantic difference;
4. assess customer/batch impact;
5. never alter historical persisted results.

# 25. Observability

Metrics:
- evaluations/sec;
- failures by type;
- rule not found;
- invalid input;
- engine errors;
- cache hit;
- simulation volume;
- release blockers by reason.

# 26. Implementation Sequence

1. decimal library;
2. UOM catalogue;
3. AST schema;
4. parser/type checker;
5. safe evaluator;
6. test-vector harness;
7. rule persistence/versioning;
8. release workflow/Vault;
9. runtime evaluation API;
10. explanation/reason codes;
11. authoring UI;
12. impact analysis.

