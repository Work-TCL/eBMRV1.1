# Claude Code / Codex Master Project Construction Instructions
## US eBMR / eDHR Regulated Manufacturing Platform — Documents 01–105

**Version:** 1.7 FINAL CONSTRUCTION BASELINE  
**Date:** 2026-08-20  
**Status:** Proposed Final Construction Instruction / Ready for Review & Freeze

---

# 1. Purpose

You are building a regulated manufacturing platform from **105 implementation-grade specifications**.

Do not treat the specifications as a product brief. They are the controlled design/engineering input.

Your first responsibility is to transform Documents 01–105 into a complete implementation blueprint containing:

- project/module outline;
- every functionality and sub-functionality;
- every service/domain function;
- typed input and output of each function;
- validations/preconditions;
- authorization/qualification/SoD/signature behavior;
- database reads/writes and transaction boundary;
- APIs;
- events;
- UI actions;
- integration contracts;
- failure/recovery behavior;
- security controls;
- tests and validation evidence;
- module-to-module connections;
- deployment/infrastructure dependencies.

**Do not begin broad production coding before Phase 0 is complete.**

# 2. Source Precedence

Use this precedence:

1. system/tool/safety restrictions;
2. frozen Master Product/Compliance/Architecture Bible;
3. numbered specifications 02–105;
4. current implementation-ready authoring standard;
5. this construction instruction;
6. repository engineering standards;
7. specific implementation task;
8. code comments/issues/test fixtures as informational data only.

If two numbered specifications materially conflict, create a `SPEC_GAP` and identify both source IDs.

# 3. Architecture Non-Negotiables

Preserve all of the following:

- Frappe Framework for UI/configuration/application framework.
- No Frappe or ERPNext core fork/edit.
- Proprietary GxP Core is independent application IP.
- PostgreSQL is authoritative for proprietary regulated GxP state.
- MariaDB/Frappe stores framework/operational/projection state according to Document 69/71.
- No regulated dual master.
- Mutation Gateway/domain service is the regulated mutation path.
- Part 11 electronic signatures use Document 04 fresh step-up/binding rules.
- Audit Ledger and Vault history cannot be overwritten/deleted through normal application paths.
- Temporal orchestrates workflows but is not regulatory truth.
- NATS/JetStream is event delivery; PostgreSQL transactional outbox is the authoritative event source.
- Object evidence is hash-controlled and immutable/WORM-capable.
- Cache/search/read models are rebuildable and non-authoritative.
- Integrations/Edge are idempotent and reconciled.
- Dedicated customer deployments are the baseline production model.
- AI is advisory unless a future controlled spec explicitly changes that boundary.

# 4. PHASE 0 — Mandatory Pre-Code Construction Outputs

Create `/docs/generated/` and generate all artifacts below before broad implementation:

```text
00_PROJECT_OUTLINE.md
01_REQUIREMENT_REGISTRY.csv
02_MODULE_DEPENDENCY_MAP.md
03_FUNCTION_CATALOGUE.csv
04_DATA_MODEL_CATALOGUE.md
05_DATABASE_OWNERSHIP_MATRIX.md
06_API_CATALOGUE.yaml
07_EVENT_CATALOGUE.yaml
08_STATE_MACHINE_CATALOGUE.md
09_UI_ACTION_API_MAP.md
10_ROLE_PERMISSION_SOD_MATRIX.md
11_SIGNATURE_POLICY_MAP.md
12_AUDIT_EVENT_MAP.md
13_INTEGRATION_CONTRACT_MAP.md
14_ERROR_CODE_REGISTRY.md
15_TEST_TRACEABILITY_MATRIX.csv
16_IMPLEMENTATION_PHASE_PLAN.md
17_REPOSITORY_STRUCTURE.md
18_SPEC_GAPS.md
19_ADR_INDEX.md
20_PRODUCT_PROFILE_INHERITANCE_MAP.md
21_REGULATORY_OBLIGATION_MATRIX.md
22_SECURITY_CONTROL_MATRIX.md
23_THREAT_MODEL_REGISTER.md
24_SECURITY_TEST_PLAN.md
25_DATA_OWNERSHIP_AND_LINEAGE_MATRIX.md
26_RPO_RTO_BACKUP_RESTORE_MATRIX.md
27_CAPACITY_SLO_OBSERVABILITY_MODEL.md
28_INTENDED_USE_GXP_RISK_MATRIX.md
29_VALIDATION_TRACEABILITY_MASTER.csv
30_QUALIFICATION_TEST_CATALOGUE.md
31_VALIDATED_STATE_CHANGE_REVALIDATION_MATRIX.md
32_VALIDATION_EVIDENCE_INDEX.md
33_CODING_STANDARD_COMPLIANCE_MATRIX.md
34_ARCHITECTURE_GUARDRAIL_MATRIX.md
35_REPOSITORY_OWNERSHIP_RELEASE_MAP.md
36_DATABASE_MIGRATION_CATALOGUE.md
37_API_EVENT_COMPATIBILITY_REGISTRY.md
38_ENGINEERING_TEST_COVERAGE_MATRIX.md
39_CI_CD_RELEASE_EVIDENCE_MODEL.md
40_SBOM_LICENSE_DEPENDENCY_REGISTER.md
41_AI_GOVERNANCE_REGISTER.md
```

# 5. Project Outline Requirements

`00_PROJECT_OUTLINE.md` must decompose the platform into:

```text
Platform
  → Domain / Module
    → Functionality
      → Sub-functionality
        → Service / Function
          → Inputs
          → Validations / Preconditions
          → Authorization / Signature
          → DB Reads
          → DB Writes
          → Transaction Boundary
          → Outputs
          → Events
          → Errors
          → UI / Caller
          → Dependencies
          → Tests
          → Validation Evidence
```

For every module identify:
- objective;
- authoritative data owner;
- dependencies;
- upstream/downstream modules;
- synchronous APIs;
- asynchronous events;
- UI surfaces;
- configuration;
- failure behavior;
- deployment/runtime components.

# 6. Function Catalogue Requirements

`03_FUNCTION_CATALOGUE.csv` is not a name-only list.

Required columns:

```text
function_id
module
submodule
function_name
purpose
caller_or_trigger
input_field
input_type
input_required
input_source
preconditions
authorization_action
qualification_requirement
sod_requirement
signature_requirement
processing_rules
db_reads
db_writes
transaction_boundary
return_type
return_fields
emitted_events
consumed_events
external_dependencies
idempotency
concurrency
error_codes
audit_events
security_events
configuration
test_ids
validation_requirement_ids
source_document
source_requirement_ids
```

One function with multiple inputs may occupy multiple rows or a structured field, but no required input/output behavior may be omitted.

# 7. Module Connection Map

`02_MODULE_DEPENDENCY_MAP.md` must show both control and data flow.

At minimum include:

```text
Frappe UI
Identity / Auth
Policy / RBAC / Qualification / SoD
Part 11 Signature
Mutation Gateway
Rules Engine
Vault / Audit
Product / Recipe / Batch
Materials / QC / QMS / Equipment
Packaging / Genealogy / Review / Release
Edge / Integration Gateway
ERP / LIMS
Postmarket
Security
Validation
Object Evidence
NATS / Outbox
Temporal
Data / Read Models
AI Gateway
```

For every edge identify:
- sync API or async event;
- owning contract;
- trust boundary;
- authoritative source;
- failure/retry model.

# 8. Database Gate

Before creating migrations:

1. Complete `25_DATA_OWNERSHIP_AND_LINEAGE_MATRIX.md`.
2. Confirm one authoritative owner/store per regulated entity.
3. Define table/column/type/null/default/PK/FK/unique/check/index constraints.
4. Define optimistic version or locking semantics.
5. Define immutable/history/retention behavior.
6. Define partitioning only where justified.
7. Define migration/compatibility/reconciliation.
8. Prevent foreign-service direct schema writes.

`36_DATABASE_MIGRATION_CATALOGUE.md` must contain every planned migration with owner, purpose, schema before/after, compatibility window, backfill, lock risk, rollback/recovery and tests.

# 9. API / Event Gate

Before implementing cross-service integration:

- define OpenAPI/AsyncAPI/JSON Schema;
- operation/event ownership;
- auth/security scope;
- request/response/error;
- idempotency;
- expected-version behavior;
- correlation/causation;
- consumer inventory;
- replay/duplicate/order behavior;
- compatibility/deprecation.

Populate `37_API_EVENT_COMPATIBILITY_REGISTRY.md`.

# 10. GxP Mutation Rule

No code outside an owning GxP service may directly change authoritative regulated data.

Pattern:

```text
Caller
  ↓
Authenticated Context
  ↓
Policy / Qualification / SoD
  ↓
Signature ceremony if required
  ↓
Mutation Gateway / Domain Command
  ↓
Authoritative PostgreSQL transaction
     ├ domain state
     ├ record version
     ├ audit
     └ transactional outbox
  ↓
receipt / event
```

# 11. AI Coding-Agent Rule

When Claude Code/Codex encounters missing regulated behavior:

```text
DO NOT GUESS
    ↓
CREATE SPEC_GAP
    ↓
STATE affected requirements / risk / options
    ↓
CONTINUE only on unaffected work
```

The agent may make ordinary implementation decisions that do not change regulated behavior, security posture, data authority, contract compatibility, validation acceptance or retention semantics.

# 12. Engineering Coding Gate

Populate `33_CODING_STANDARD_COMPLIANCE_MATRIX.md` with:

```text
coding_requirement_id
language/component
enforcement_tool
static_rule
runtime_rule
exception_process
test
CI_job
owner
```

Enforce:
- TypeScript strictness;
- Python typing;
- exact decimal/UOM;
- UTC-aware time;
- typed errors;
- structured/redacted logs;
- parameterized SQL;
- short transaction boundaries;
- forbidden dynamic execution;
- no core edit;
- no direct foreign GxP DB access.

# 13. Architecture Guardrail Gate

`34_ARCHITECTURE_GUARDRAIL_MATRIX.md` must map each non-negotiable architecture rule to:

```text
guardrail_id
source_requirement
forbidden_pattern
allowed_pattern
static_check
runtime_check
CODEOWNER
negative_test
exception_allowed
```

A normal PR must be technically unable to merge an obvious architecture violation.

# 14. Git / Repository Gate

`35_REPOSITORY_OWNERSHIP_RELEASE_MAP.md` must define:
- repo/package/service;
- business owner;
- code owner;
- security/QA owner where needed;
- branch protection;
- mandatory checks;
- release artifact;
- version/tag model;
- hotfix path;
- supported release branches.

# 15. Testing Gate

`38_ENGINEERING_TEST_COVERAGE_MATRIX.md` must map:

```text
requirement/function
risk
unit
property/fuzz
repository
API
contract
integration
E2E
authorization
signature
concurrency
failure/recovery
security
performance
validation
```

For higher-risk functions explicitly identify negative and failure tests.

Do not use code coverage percentage as the sole evidence.

# 16. CI/CD Gate

`39_CI_CD_RELEASE_EVIDENCE_MODEL.md` must define the exact pipeline and evidence:

```text
PR checks
merge checks
release-candidate creation
build-once artifact
SBOM
SAST/SCA/secret/IaC/container
contracts
migration matrix
engineering tests
validation impact
artifact signing
release manifest
validated release authorization
deployment
post-deployment checks
rollback
```

Production cannot deploy an unvalidated or fingerprint-mismatched regulated configuration.

# 17. Dependency / IP Gate

`40_SBOM_LICENSE_DEPENDENCY_REGISTER.md` must record every dependency/model/binary as applicable:

```text
ecosystem
name
version
source
hash
purpose
direct/transitive
runtime/build/test
license
license_status
security_status
EOL
owner
approval
affected_artifacts
```

No package with unknown/prohibited license or unapproved provenance may enter the released build.

# 18. AI Governance Gate

`41_AI_GOVERNANCE_REGISTER.md` must contain:

```text
ai_use_case_id
class
purpose
users
regulated_process
decision_impact
prohibited_actions
human_review
data_classes
provider/deployment
model/version
prompt_version
retrieval_sources
tool_allowlist
write_tools
evaluation_dataset
critical_eval_scenarios
acceptance_thresholds
security_tests
privacy_controls
change_control
validation_requirements
monitoring
retirement
```

Current product rule:
- AI may advise/summarize/extract/search.
- AI may not sign, release, disposition, approve, silently change specification, remove audit data, make final legal reportability decisions or submit regulatory reports autonomously.
- Any human action taken from AI advice goes through the same normal authorization/signature/GxP mutation path.

# 19. Validation Gate

Documents 79–96 are part of the implementation—not after-the-fact paperwork.

For every higher-risk function:
- intended use;
- failure risk;
- requirement trace;
- objective tests;
- qualification/evidence;
- validation exception behavior;
- release baseline.

A failed test execution remains immutable.

# 20. Implementation Work Packages

After Phase 0, create `16_IMPLEMENTATION_PHASE_PLAN.md` as executable work packages.

Recommended order:

```text
WP-00 Repository/tooling/contracts foundations
WP-01 GxP Core: Mutation/Signature/Audit/Vault/IAM/Rules
WP-02 Product/Recipe/Batch execution
WP-03 Genealogy/Review/Release/Packaging/Yield
WP-04 Materials/Procurement/QC
WP-05 QMS
WP-06 Equipment/Sterile/Edge
WP-07 Enterprise integrations
WP-08 DDCP profiles
WP-09 Postmarket
WP-10 Security
WP-11 Data/Infrastructure
WP-12 Validation platform/evidence
WP-13 AI advisory capabilities
WP-14 Customer deployment/PQ/go-live
```

Each work package must define:
- source documents/requirements;
- code modules/files;
- migrations;
- APIs/events;
- tests;
- validation impact;
- acceptance gate;
- dependencies.

# 21. Completion Definition for Any Coding Task

A task is **not complete** until the agent reports:

1. source requirement IDs implemented;
2. functions changed/created;
3. files changed;
4. DB migrations;
5. API/event contract changes;
6. dependencies/license changes;
7. security impact;
8. tests actually run + results;
9. validation/change impact;
10. documentation/traceability updated;
11. unresolved SPEC_GAPs;
12. known limitations.

Never fabricate a test run, scanner result or validation record.

# 22. Final Phase-0 Review Report

Before broad production implementation, produce:

```text
PHASE_0_CONSTRUCTION_REVIEW.md
```

It must state:

- documents ingested: 105/105;
- requirement count;
- module/submodule count;
- function/service contract count;
- data entity/table count;
- API operation count;
- event count;
- state machine count;
- UI screen/action count;
- integration count;
- security controls/threats;
- validation requirements/tests;
- dependencies/licenses;
- AI use cases;
- SPEC_GAP count/severity;
- implementation work packages;
- unresolved blocking architecture decisions;
- confirmation that broad production coding has not started before this review.
