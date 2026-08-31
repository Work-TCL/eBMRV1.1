# US eBMR / eDHR Regulated Manufacturing Platform
## Document 02 — System Architecture & GxP Core Technical Specification — v1.0

**Parent Document:** Document 01 — Master Product, Compliance & Architecture Bible v1.1 (FROZEN)  
**Document Status:** Architecture Baseline for Detailed Module Specifications  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products (DDCP)  
**Future Profiles:** Medical Devices, Pharmaceuticals  
**Primary Application Framework:** Frappe Framework  
**Regulatory Trust Layer:** Proprietary GxP Core  
**Frozen Date:** 2026-08-20

---

# 1. PURPOSE

This document converts the frozen requirements in Document 01 into an implementable technical architecture.

It defines:

- system boundaries;
- service responsibilities;
- Frappe responsibilities;
- proprietary eBMR/eDHR responsibilities;
- proprietary GxP responsibilities;
- databases and data ownership;
- API boundaries;
- regulated mutation flow;
- electronic-signature architecture;
- immutable audit architecture;
- record versioning and locking;
- workflow orchestration;
- genealogy;
- release/disposition architecture;
- QMS technical boundaries;
- regulated procurement/material architecture;
- QC/LIMS integration;
- sterile/aseptic integration architecture;
- identity and authorization;
- Edge Gateway;
- ERP/LIMS/equipment connectors;
- event architecture;
- security architecture;
- deployment and environment topology;
- availability, backup and disaster recovery;
- validation/CSA architecture;
- observability;
- AI boundaries;
- development repository structure;
- CI/CD;
- technical rules that developers and AI coding agents must not violate.

Document 02 does **not** replace the detailed specifications listed in Document 01. It defines the architecture within which those specifications must operate.

---

# 2. RELATIONSHIP TO DOCUMENT 01

Document 01 remains the product and regulatory source of truth.

Document 02 shall not silently change any frozen Document 01 decision.

If an implementation decision conflicts with Document 01:

1. implementation stops for the affected requirement;
2. a documented architecture/product change request is created;
3. compliance and validation impact is assessed;
4. Document 01 is revised if the product requirement itself changes;
5. Document 02 is revised if only the architecture changes.

---

# 3. MANDATORY FUNCTIONAL DECOMPOSITION RULE

Every major function implemented under this architecture shall be decomposed as:

```text
Module
  ↓
Functionality
  ↓
Sub-functionality
  ↓
State / data / rule behavior
  ↓
Security & authorization
  ↓
Audit & signature behavior
  ↓
Integration behavior
  ↓
Failure behavior
  ↓
Validation / test requirement
```

No implementation ticket may simply say:

> “Build CAPA”  
> “Build Batch Execution”  
> “Build Electronic Signature”  
> “Build Audit”

without the applicable sub-functionalities and acceptance criteria.

Large functions receive dedicated downstream specifications.

---

# 4. ARCHITECTURE GOALS

The architecture shall optimize for:

1. **Regulatory trust** — electronic records must remain attributable, complete, durable, reviewable and protected.
2. **Product independence** — DDCP, Device and Pharma profiles reuse the same platform.
3. **ERP independence** — SAP, Oracle, Dynamics, ERPNext or native procurement may be used through adapters.
4. **LIMS independence** — native basic QC and external LIMS coexist.
5. **Cloud independence** — core product behavior cannot require one cloud vendor.
6. **Customer isolation** — major regulated customers receive isolated deployments/data stores.
7. **Acquisition-ready IP** — proprietary value remains clearly separated from third-party frameworks.
8. **Validation readiness** — requirements, code, releases and tests remain traceable.
9. **Controlled configurability** — customers may configure manufacturing within approved boundaries without uncontrolled code.
10. **Operational resilience** — manufacturing data is not lost because of short network or application outages.
11. **Security by design** — least privilege, strong identity, controlled administrative access and full auditability.
12. **No unnecessary distributed complexity** — use separately bounded services only where trust, scaling, failure isolation or integration justify them.

---

# 5. ARCHITECTURE PRINCIPLES — NON-NEGOTIABLE

| ID | Principle | Rule |
|---|---|---|
| ARC-001 | GxP Core is authoritative | Frappe must never be the sole authority for released or executed regulated records. |
| ARC-002 | No uncontrolled direct mutation | Regulated mutations must pass through the GxP Mutation Gateway. |
| ARC-003 | No destructive correction | Corrections create controlled new versions/events; original evidence remains. |
| ARC-004 | No distributed two-phase commit | Cross-database consistency uses authoritative transactions, idempotency, outbox/events and projections. |
| ARC-005 | Frappe is application platform | Frappe provides UI/configuration/workspaces/reporting and selected draft/master functions. |
| ARC-006 | GxP database is separate | Regulated authoritative state uses PostgreSQL controlled by GxP services. |
| ARC-007 | Audit is independent | Audit truth is not Frappe Version history or generic application logs. |
| ARC-008 | Signature is independent | Login state or a normal Frappe approval click is not a regulated signature. |
| ARC-009 | Workflow engine is not record truth | Temporal coordinates work; PostgreSQL GxP records remain authoritative. |
| ARC-010 | Integration never bypasses controls | ERP, LIMS, Edge and APIs use the same GxP mutation/rules pathways as UI actions. |
| ARC-011 | Released master is immutable | Released recipe/specification/document versions are frozen and referenced by immutable ID/hash. |
| ARC-012 | Customer code forks are avoided | Variability is configuration/profile based unless a controlled product feature is required. |
| ARC-013 | High-frequency telemetry stays outside Frappe | Historian/time-series/object storage holds raw telemetry; eBMR stores controlled evidence references/results. |
| ARC-014 | Security decision is server-side | Hidden buttons, disabled fields and browser logic are not authorization. |
| ARC-015 | Every regulated action is attributable | Human, service, machine and integration identities are distinguishable. |
| ARC-016 | UTC is authoritative | Regulated timestamps are stored in UTC; local timezone is presentation/context metadata. |
| ARC-017 | Version every regulated schema/rule | Recipe, specification, rule, workflow, event and API schemas are versioned. |
| ARC-018 | AI has no privileged bypass | AI uses normal authorized APIs and cannot directly mutate released records. |

---

# 6. MAJOR ARCHITECTURE DECISIONS

## 6.1 Decision summary

| ADR | Decision | Frozen choice |
|---|---|---|
| ADR-001 | Application framework | Frappe |
| ADR-002 | Frappe operational DB | MariaDB initially |
| ADR-003 | GxP authoritative DB | PostgreSQL |
| ADR-004 | Identity abstraction | Keycloak-compatible; customer SSO supported |
| ADR-005 | Signature authentication | Mandatory step-up for regulated signatures |
| ADR-006 | Durable workflow | Temporal adopted for long-running execution orchestration |
| ADR-007 | Policy engine | Proprietary Policy/Authorization Service initially; OPA-compatible boundary retained |
| ADR-008 | Asynchronous event bus | NATS-compatible event bus recommended; transactional outbox is source |
| ADR-009 | Object/evidence storage | S3-compatible abstraction; AWS S3 / Azure Blob reference implementations |
| ADR-010 | Service language | TypeScript/Node.js LTS for proprietary GxP services and Edge; Python remains Frappe application language |
| ADR-011 | API definition | OpenAPI + JSON Schema; AsyncAPI/event schemas for event contracts |
| ADR-012 | Deployment | Containers/Kubernetes-compatible; dedicated customer environments |
| ADR-013 | V1 offline | Edge buffering + local/private deployment resilience; no disconnected Part 11 browser execution |
| ADR-014 | Authorization | RBAC + qualification + contextual policy + segregation-of-duties |
| ADR-015 | Audit tamper evidence | Immutable event records + record-stream hash chain + periodic signed integrity checkpoint |
| ADR-016 | Generic CRUD | Prohibited for released/regulated records |
| ADR-017 | Integration pattern | Adapter interfaces with idempotent commands and reconciliation |
| ADR-018 | AI | Advisory only in V1 |

## 6.2 Why TypeScript for proprietary GxP services

The proprietary GxP layer benefits from:

- explicit interface contracts;
- strong compile-time typing;
- JSON/OpenAPI/event-schema alignment;
- good support for API, event and edge integration;
- shared validation schemas between services and integration tooling;
- team-friendly modular service development.

Recommended implementation style:

```text
Node.js LTS
TypeScript
NestJS with Fastify adapter OR equivalent structured service framework
PostgreSQL
OpenAPI
JSON Schema
OpenTelemetry
```

The exact runtime/framework version shall be pinned per validated release and recorded in the SBOM.

---

# 7. SYSTEM CONTEXT

```text
                         ┌──────────────────────┐
                         │   Production Users   │
                         │ Operator / QA / QC   │
                         │ Warehouse / Eng.     │
                         └──────────┬───────────┘
                                    │ HTTPS
                                    ▼
                        ┌────────────────────────┐
                        │ Web / Application Tier │
                        │      Frappe UI         │
                        └───────────┬────────────┘
                                    │
                         Regulated API boundary
                                    │
                                    ▼
┌─────────────┐          ┌────────────────────────┐          ┌───────────────┐
│ Keycloak /  │◄────────►│   PROPRIETARY GxP     │◄────────►│ Temporal      │
│ Customer IdP│          │        CORE            │          │ Orchestrator  │
└─────────────┘          └───────────┬────────────┘          └───────────────┘
                                     │
                  ┌──────────────────┼──────────────────┐
                  │                  │                  │
                  ▼                  ▼                  ▼
            PostgreSQL        Audit / Vault       Event / Outbox
              GxP DB             Storage              Bus
                  │
        ┌─────────┼──────────┬───────────┐
        │         │          │           │
        ▼         ▼          ▼           ▼
      ERP       LIMS     Edge Gateway  Evidence/Object
    Adapter    Adapter   PLC/Lab/Scan      Storage
```

---

# 8. TRUST ZONES

The architecture shall separate at least the following logical trust zones.

| Zone | Contents | Trust level | Key rule |
|---|---|---|---|
| Z1 Public/Client | Browser/mobile client | Untrusted | Never trusted for authorization or regulated timestamps |
| Z2 Application | Frappe/web tier | Semi-trusted | May request regulated actions but cannot bypass GxP APIs |
| Z3 GxP Core | Mutation, signature, audit, rules, release | Highest application trust | Only controlled service identities and network paths |
| Z4 Data | PostgreSQL/MariaDB/object storage | Restricted | No public access; privileged access logged |
| Z5 Integration | ERP/LIMS/Edge adapters | Controlled external | mTLS/OAuth; per-adapter scopes |
| Z6 Identity | Keycloak/customer IdP | Security critical | Separate admin roles; no application DB password storage |
| Z7 Operations | CI/CD, monitoring, backup | Privileged | Segregated operational identities and audit |
| Z8 Factory Edge | Plant network/Edge Gateway | Controlled local | Device identity, buffering, source validation |

---

# 9. DEPLOYMENT TOPOLOGIES

## 9.1 Dedicated SaaS

```text
Customer A VPC/VNet/Namespace
├── Frappe application
├── MariaDB
├── GxP Core
├── PostgreSQL
├── Temporal workers
├── Identity broker/integration
├── Event infrastructure
├── Evidence storage
└── Customer-specific connectors

Customer B
└── Separate equivalent environment
```

No regulated database rows are shared across unrelated enterprise customers unless a future explicitly validated multi-tenant edition is created.

## 9.2 Customer private cloud

Same logical services deployed into customer-controlled AWS/Azure/cloud environment.

Responsibilities shall be divided by deployment agreement:

- application operation;
- database operation;
- backup;
- identity;
- network;
- monitoring;
- incident response;
- patching;
- validation evidence.

## 9.3 On-premise / plant private environment

Containerized deployment with:

- internal ingress;
- customer IdP or local Keycloak;
- local GxP services;
- local DB;
- local object/evidence storage;
- local Edge Gateway;
- outbound-only optional support/telemetry channel.

The system shall operate without dependence on public internet when deployed fully on-premise.

---

# 10. APPLICATION LAYER — FRAPPE RESPONSIBILITIES

Frappe is used for rapid enterprise application development but is not the regulatory trust authority.

## 10.1 Frappe responsibilities

- login/SSO front-end integration;
- application navigation/workspaces;
- configuration UI;
- master-data authoring UI;
- draft recipe/specification authoring UI;
- dashboards;
- reports and list views;
- notifications;
- non-regulated preferences;
- attachment upload interface;
- customer configuration;
- reference data;
- administrative screens;
- read models/projections of GxP data;
- native procurement/material UI where applicable;
- QMS UI;
- QC UI;
- integration administration.

## 10.2 Frappe must not directly own

- released recipe truth;
- released specification truth;
- executed batch-step truth;
- regulated electronic signatures;
- authoritative audit history;
- final batch release;
- final disposition;
- immutable correction history;
- authoritative genealogy;
- regulated evidence integrity;
- Part 11 signature challenge;
- released record locking.

## 10.3 Frappe data categories

### Category A — Non-regulated application/configuration

May be normal Frappe DocTypes.

Examples:

- UI preferences;
- notification settings;
- dashboard layouts;
- non-regulated integration configuration metadata.

### Category B — Controlled authoring objects

May be authored in Frappe, but release requires GxP Core.

Examples:

- recipe draft;
- specification draft;
- SOP metadata draft;
- training curriculum draft;
- equipment master draft;
- supplier qualification draft.

### Category C — GxP projections/read models

Frappe displays a projection of records whose truth is in GxP Core.

Examples:

- released recipe version;
- active batch header;
- signed step result;
- released batch;
- audit summary;
- genealogy summary.

### Category D — Prohibited direct CRUD

Regulated authoritative records shall not be modified through generic Frappe REST CRUD or direct DocType writes.

---

# 11. PROPRIETARY GxP CORE — COMPONENT MAP

```text
GxP Core
│
├── Mutation Gateway
├── Identity Context Service
├── Authorization / Policy Service
├── Electronic Signature Service
├── Audit Ledger Service
├── Record Version Vault
├── Recipe Release Service
├── Batch / Execution Service
├── Rules & Calculation Service
├── Material Eligibility Service
├── Equipment Eligibility Service
├── Qualification Service
├── Genealogy Service
├── Quality Event Service
├── Release / Disposition Service
├── Evidence Service
├── Regulatory Export Service
├── Integration Command Service
└── Compliance Reporting Service
```

Services may initially be deployed as a limited number of independently bounded applications rather than one container per box.

Logical boundaries are mandatory even if deployment units are consolidated.

---

# 12. GxP MUTATION GATEWAY

## 12.1 Purpose

The Mutation Gateway is the sole supported entry point for regulated record changes.

It prevents:

- uncontrolled Frappe database updates;
- direct integration writes;
- UI-only validation;
- unsigned approval changes;
- missing reason-for-change;
- state transition bypass;
- inconsistent audit creation.

## 12.2 Required sub-functionalities

| ID | Sub-function | Behavior |
|---|---|---|
| MUT-001 | Identity validation | Resolve human/service/device identity from verified token/certificate |
| MUT-002 | Tenant/site scope | Confirm request belongs to authorized customer/site |
| MUT-003 | Authorization | Evaluate roles, permissions, qualification and SoD |
| MUT-004 | State validation | Ensure current record state permits requested operation |
| MUT-005 | Version check | Reject stale write using expected record version/ETag |
| MUT-006 | Reason enforcement | Require reason for controlled correction/override/change |
| MUT-007 | Rule validation | Execute domain rules before mutation |
| MUT-008 | Signature requirement | Determine whether step-up signature is required |
| MUT-009 | Idempotency | Same command/idempotency key cannot create duplicate regulated action |
| MUT-010 | Transaction | Persist business event + audit event atomically within authoritative GxP DB |
| MUT-011 | Outbox | Persist integration/event outbox in same transaction |
| MUT-012 | Result hash | Compute canonical resulting record hash |
| MUT-013 | Response evidence | Return immutable record/version/event identifiers |
| MUT-014 | Failure audit | Security-sensitive failed attempts recorded when appropriate |
| MUT-015 | Correlation | Attach correlation/causation IDs across services |

## 12.3 Command pattern

Example:

```json
{
  "command_id": "uuid",
  "command_type": "CompleteBatchStep",
  "aggregate_type": "Batch",
  "aggregate_id": "BATCH-123",
  "expected_version": 44,
  "actor_context": "...token-derived...",
  "payload": {},
  "reason": null,
  "idempotency_key": "..."
}
```

Client-provided actor identity fields are never trusted. Actor identity is derived from authenticated server-side context.

---

# 13. AUTHORITATIVE TRANSACTION MODEL

## 13.1 No distributed two-phase commit

MariaDB and PostgreSQL are not committed using a cross-database 2PC transaction.

For regulated operations:

```text
UI/Frappe
   ↓ command
GxP Mutation Gateway
   ↓
PostgreSQL transaction
   ├── Business state
   ├── Record version
   ├── Audit event
   └── Outbox event
COMMIT
   ↓
Acknowledgement
   ↓
Projection/event updates Frappe
```

If the Frappe projection update fails:

- the GxP record remains valid;
- the event is retried;
- projection health is visible;
- no user is told the regulated operation failed if the authoritative commit succeeded.

## 13.2 Release of a master authored in Frappe

```text
Recipe Draft in Frappe
   ↓
User requests release
   ↓
Canonical payload generated
   ↓
GxP validates
   ↓
Step-up signatures
   ↓
Immutable recipe version + hash + audit committed
   ↓
Release event
   ↓
Frappe shows Released Version ID
```

The original Frappe draft may remain for authoring history, but batches reference the GxP released version ID/hash.

---

# 14. ELECTRONIC SIGNATURE SERVICE

## 14.1 Architecture

```text
User clicks regulated Sign/Approve/Release
       ↓
GxP creates Signature Challenge
       ├── record ID
       ├── record version
       ├── record hash
       ├── signature meaning
       ├── nonce
       └── expiry
       ↓
Frontend initiates IdP step-up authentication
       ↓
Keycloak / Customer IdP authenticates
       ↓
GxP verifies returned authentication context
       ↓
Signature record committed
       ↓
Audit event committed
       ↓
Record transition completed
```

## 14.2 Required sub-functionalities

| ID | Sub-function | Requirement |
|---|---|---|
| SIG-001 | Signature challenge | Unique, short-lived, single-use challenge |
| SIG-002 | Record binding | Challenge binds record ID, version and hash |
| SIG-003 | Meaning | Meaning is explicit: performed, verified, reviewed, approved, released, rejected, etc. |
| SIG-004 | Step-up | IdP must perform configured fresh authentication |
| SIG-005 | Authentication assurance | Capture authentication method/ACR/AMR metadata |
| SIG-006 | Identity | Immutable signer subject ID + displayed name |
| SIG-007 | Timestamp | Server UTC timestamp |
| SIG-008 | Replay prevention | Used challenge cannot be reused |
| SIG-009 | Expiry | Expired challenge requires restart |
| SIG-010 | Changed-record detection | If record hash/version changes, challenge becomes invalid |
| SIG-011 | Signature manifestation | Human-readable name, time, meaning shown/exported |
| SIG-012 | Failed attempt handling | Failures do not create a valid signature; security-relevant attempts logged |
| SIG-013 | Revoked account history | Historical signatures remain linked after account disablement |
| SIG-014 | Service separation | Admin cannot manufacture a user signature by database edit |
| SIG-015 | API signing | Human electronic signatures cannot be replaced by service account token |
| SIG-016 | Delegation prohibition | No signature delegation unless a future explicitly compliant process is designed |

## 14.3 Password handling

The eBMR application must not store user passwords.

Authentication credentials remain with:

- customer enterprise IdP;
- Keycloak where used as the identity broker/provider.

---

# 15. AUDIT LEDGER SERVICE

## 15.1 Purpose

The Audit Ledger provides independent, secure, time-stamped history of regulated actions.

## 15.2 Audit event schema

Minimum fields:

```text
event_id
event_schema_version
tenant_id
site_id
aggregate_type
aggregate_id
aggregate_version
event_type
actor_type
actor_subject_id
actor_display_name
role_context
source_type
source_id
timestamp_utc
server_node
request_id
correlation_id
causation_id
old_value/reference
new_value/reference
changed_fields
reason
signature_id
rule_version
application_version
previous_record_event_hash
event_hash
```

## 15.3 Required sub-functionalities

- append-only event creation;
- no application UPDATE;
- no application DELETE;
- old/new information;
- actor attribution;
- timestamp;
- reason;
- signature linkage;
- service/device attribution;
- event search;
- record-centric audit view;
- batch-centric audit view;
- user-centric audit view;
- security-sensitive audit view;
- export;
- integrity verification;
- retention;
- archival;
- privileged-access monitoring;
- schema versioning.

## 15.4 Tamper-evidence model

A single global blockchain-like chain is **not** required.

Recommended scalable model:

### Per-record stream integrity

```text
Record Event 1
   ↓ hash
Record Event 2
   ↓ hash
Record Event 3
```

Each event hash includes canonical event content and the prior event hash for that regulated aggregate.

### Periodic integrity checkpoint

At a configured interval:

1. current audit event hashes are collected;
2. an integrity manifest/Merkle root is generated;
3. root is signed using controlled KMS/HSM-backed key;
4. manifest is stored in immutable/WORM-capable storage;
5. verification job confirms ledger integrity.

This is a technical hardening mechanism, not a substitute for validation or procedural controls.

---

# 16. RECORD VERSION VAULT

## 16.1 Purpose

The Vault preserves canonical regulated versions independent of mutable Frappe authoring objects.

## 16.2 Vault object types

- released recipe;
- released product specification;
- released material specification;
- released equipment/process specification;
- released SOP/document metadata/package;
- batch creation snapshot;
- completed batch record version;
- corrected/superseding batch record;
- QA release package;
- signed export package;
- evidence manifest.

## 16.3 Canonicalization and hashing

Before hashing:

- canonical JSON representation shall be used;
- ordering is deterministic;
- timestamps use normalized format;
- decimal numbers use controlled precision rules;
- no UI-only/transient values are included.

Recommended digest: SHA-256 or stronger approved algorithm.

Hash algorithm identifiers are stored with each digest to permit future algorithm migration.

## 16.4 Correction behavior

Released records are never edited in place.

```text
Released Record V1
      ↓ correction request
Controlled Correction
      ↓
Record V2 / Amendment
      ↓
V1 remains permanently retrievable
```

---

# 17. RECIPE / MASTER MANUFACTURING ARCHITECTURE

## 17.1 Logical model

```text
Product
  └── Manufacturing Profile
       └── Recipe Family
            └── Recipe Version
                 ├── Materials
                 ├── Equipment requirements
                 ├── Personnel/qualification requirements
                 ├── Step graph
                 ├── Parameters
                 ├── Calculations
                 ├── IPC/QC
                 ├── Signatures
                 ├── Evidence requirements
                 └── Release rules
```

## 17.2 Required sub-functionalities

- draft creation;
- copy/version;
- structured step definition;
- ordered and parallel steps;
- conditional branches;
- reusable step templates;
- required material definition;
- allowed material alternative rules;
- equipment class/asset requirements;
- operator qualification requirements;
- parameter type/units;
- target/min/max;
- data source: manual/device/calculated/LIMS/ERP;
- verification requirement;
- signature requirement;
- hold points;
- timers;
- evidence/attachment requirements;
- calculation version;
- QC sampling point;
- deviation behavior;
- release dependency;
- approval;
- effective dating;
- obsolescence;
- emergency controlled replacement;
- immutable release.

Detailed behavior belongs in SPEC-EBMR-001.

---

# 18. BATCH EXECUTION ARCHITECTURE

## 18.1 Authoritative batch state

Batch state is stored in GxP PostgreSQL.

Frappe displays the state but does not independently transition it.

## 18.2 Reference state machine

```text
Planned
  ↓
Created / Snapshot Locked
  ↓
Issued
  ↓
Ready
  ↓
In Execution
  ├── On Hold
  ├── Exception Pending
  └── In Execution
  ↓
Production Complete
  ↓
QA Review
  ├── Returned for Controlled Action
  └── QA Review
  ↓
Released / Rejected / Other Disposition
  ↓
Closed
```

Exact state names remain configurable only within approved product rules.

## 18.3 Step states

```text
Not Ready
Ready
In Progress
Paused
Completed
Exception
Voided by controlled procedure
Superseded / Corrected
```

## 18.4 Required sub-functionalities

- batch creation from released recipe;
- immutable snapshot;
- step readiness calculation;
- performer qualification check;
- area/site check;
- equipment check;
- material check;
- step start;
- data capture;
- device data capture;
- calculation;
- verification;
- signature;
- step complete;
- pause/resume;
- hold;
- exception;
- conditional branch;
- parallel step synchronization;
- timer/hold-time enforcement;
- shift handover;
- controlled correction;
- rework/reprocess branch;
- abort/reject/disposition;
- QA review;
- final closure.

---

# 19. TEMPORAL ORCHESTRATION ARCHITECTURE

Temporal is adopted for durable long-running orchestration.

## 19.1 Temporal shall manage

- wait states;
- timers;
- retryable external calls;
- long-running process coordination;
- parallel branches;
- asynchronous callbacks;
- escalation timers;
- recovery after worker restart;
- workflow-level timeout.

## 19.2 Temporal shall NOT be authoritative for

- regulated batch values;
- audit trail;
- signatures;
- released recipe;
- material genealogy;
- final disposition.

## 19.3 Workflow rules

- workflow code must be deterministic;
- external actions happen through Activities;
- Activities must be idempotent;
- regulated mutations call GxP APIs;
- workflow history stores IDs/references, not unnecessary sensitive/full batch payloads;
- workflow versioning is mandatory;
- long histories use appropriate continuation/history management;
- workflow IDs include tenant/site/aggregate identity;
- replay testing is part of release regression.

## 19.4 Failure case

If Temporal is temporarily unavailable:

- authoritative GxP state remains intact;
- new orchestration operations may pause;
- existing evidence is not lost;
- recovery/reconciliation restarts from authoritative state.

---

# 20. POLICY / AUTHORIZATION SERVICE

## 20.1 Authorization inputs

A decision may depend on:

- user identity;
- user role;
- site;
- department;
- qualification;
- training status;
- equipment qualification;
- product;
- process step;
- batch state;
- quality-event state;
- requested action;
- previous performer/verifier;
- emergency authorization;
- time/shift;
- customer policy.

## 20.2 Example policy decision

```text
Can user QA-17 release Batch B-1008?

Checks:
✓ user active
✓ site access
✓ QA Release role
✓ required qualification active
✓ not production performer where independent release required
✓ no unresolved critical deviations
✓ QC release complete
✓ material reconciliation complete
✓ all required signatures valid
✓ audit integrity healthy
→ ALLOW
```

## 20.3 OPA decision

V1 shall implement a proprietary policy interface/service.

The policy API shall be designed so an OPA-based evaluator can be introduced later without changing domain services.

Reason:

- avoid unnecessary critical runtime dependency initially;
- keep regulated policy semantics under product control;
- retain future policy-as-code option.

---

# 21. RULES & CALCULATION SERVICE

## 21.1 Rule categories

- eligibility;
- limits;
- formula;
- sequence;
- required signature;
- required verification;
- hold;
- deviation trigger;
- release;
- expiry/retest;
- equipment;
- personnel qualification;
- environmental excursion;
- reconciliation.

## 21.2 Calculation controls

Each regulated calculation shall have:

- calculation ID;
- semantic version;
- input definitions;
- units;
- precision;
- rounding rule;
- formula;
- expected output;
- test cases;
- validation status;
- release status.

Arbitrary customer Python/JavaScript execution is prohibited for GxP-critical formulas.

---

# 22. GENEALOGY SERVICE

## 22.1 Purpose

Genealogy must answer forward and backward traceability across drug, device, material and finished combination product.

## 22.2 Entity types

- supplier;
- manufacturer;
- supplier lot;
- manufacturer lot;
- internal material lot;
- container;
- drug batch;
- intermediate;
- device component lot;
- device serial;
- device assembly;
- combination-product lot;
- combination-product serial;
- packaging lot;
- shipping/distribution reference;
- equipment usage;
- process step.

## 22.3 Relationship examples

```text
CONTAINS
DERIVED_FROM
CONSUMED_IN
PRODUCED_BY
ASSEMBLED_INTO
PACKAGED_AS
TESTED_BY
USED_EQUIPMENT
REWORKED_FROM
RETURNED_FROM
DISTRIBUTED_TO
```

## 22.4 Storage

V1 shall use PostgreSQL relational/graph-style edge tables and indexed traversal queries.

A dedicated graph database is **not required initially**.

The data-access layer shall keep genealogy semantics abstract enough to introduce a graph engine later if evidence demonstrates need.

## 22.5 Required queries

- raw-material lot → every affected batch/product;
- finished serial → every constituent/material lot;
- device component lot → affected combination-product units;
- supplier lot → internal lots → batches;
- batch → equipment used;
- complaint serial → manufacturing batch → material/equipment history;
- recall lot → affected shipped units.

---

# 23. MATERIAL / PROCUREMENT ARCHITECTURE

## 23.1 Ownership boundary

### eBMR/GxP owns

- supplier quality status;
- approved supplier/material relationship;
- regulated receipt evidence;
- material lot identity;
- internal container identity;
- quality status;
- sampling/QC status;
- eligibility;
- dispensing evidence;
- actual consumption evidence;
- return/destruction evidence;
- manufacturing genealogy.

### ERP may own

- commercial PO authority;
- price;
- taxes;
- accounts payable;
- financial inventory valuation;
- corporate accounting.

### Native mode

If no external ERP exists, native regulated procurement may create and manage PR/RFQ/PO/receipt workflows.

## 23.2 Inventory synchronization

Integration shall support:

- master mapping;
- PO reference;
- expected receipt;
- goods receipt;
- quantity updates;
- reservations;
- consumption;
- returns;
- adjustments;
- rejection/destruction;
- reconciliation.

Every external write uses:

- idempotency key;
- source-system ID;
- mapping ID;
- retry state;
- reconciliation state;
- audit event.

---

# 24. QC / LIMS ARCHITECTURE

## 24.1 Native Basic QC

V1 native QC shall support:

- test specification;
- test method reference;
- sampling plan;
- sample ID;
- sample chain of custody;
- test assignment;
- result entry;
- instrument/source metadata;
- acceptance limits;
- pass/fail;
- review;
- result correction/supersession;
- OOS trigger;
- OOT trigger;
- batch/material release dependency.

## 24.2 Generic LIMS adapter

Interface operations:

```text
create_sample()
cancel_sample()
get_sample_status()
get_test_order()
receive_result()
receive_result_revision()
get_coa()
get_attachment_reference()
acknowledge_result()
```

## 24.3 LIMS result rules

- external result includes source identity;
- duplicates rejected/idempotent;
- revisions create new result version;
- original result remains;
- result schema version recorded;
- invalid signature/message fails safely;
- release waits for required accepted results.

---

# 25. QMS TECHNICAL ARCHITECTURE

QMS modules use common services rather than independent one-off workflows.

## 25.1 Shared Quality Event Kernel

Shared properties:

- quality-event ID;
- type;
- source;
- severity;
- status;
- site;
- product;
- batch;
- material;
- equipment;
- personnel;
- linked events;
- owner;
- investigator;
- due date;
- risk;
- attachments;
- signatures;
- audit;
- closure evidence.

## 25.2 Modules

- deviation;
- CAPA;
- OOS;
- OOT;
- nonconformance;
- change control;
- SCAR;
- complaint;
- recall/field action;
- internal audit;
- risk.

## 25.3 Cross-event relationship model

```text
OOS ───────► Deviation
              │
              ▼
             CAPA
              │
              ▼
         Change Control
              │
              ▼
         Recipe Version

Complaint ───► CAPA
Complaint ───► Recall
NCR ─────────► Rework
```

All relationships are auditable and versioned.

---

# 26. STERILE / ASEPTIC TECHNICAL ARCHITECTURE

The sterile module is a profile-enabled layer over common execution, equipment, qualification, QC and Edge services.

## 26.1 External data sources

May include:

- environmental monitoring system;
- building management system;
- particle counter;
- viable monitoring/LIMS;
- sterilizer;
- autoclave;
- SIP/CIP controller;
- filling line;
- filter integrity tester.

## 26.2 Required technical controls

- device/source identity;
- parameter mapping;
- controlled unit conversion;
- source timestamp;
- server receive timestamp;
- quality/status code;
- threshold evaluation;
- affected time-window mapping;
- batch-step correlation;
- excursion generation;
- evidence retention;
- release blocking.

## 26.3 Environmental excursion correlation

```text
Excursion
  ├── area
  ├── start/end
  ├── parameter
  ├── severity
  └── source
       ↓
Find batches/steps active in affected area/time
       ↓
Create impact candidates
       ↓
QA assessment
       ↓
Disposition / release impact
```

---

# 27. EDGE GATEWAY ARCHITECTURE

## 27.1 Purpose

Edge Gateway isolates industrial/lab connectivity from Frappe and central GxP services.

## 27.2 Plugin model

```text
Edge Core
│
├── OPC UA Adapter
├── Modbus TCP Adapter
├── Modbus RTU Adapter
├── MQTT Adapter
├── REST Adapter
├── Serial / RS-232 Adapter
├── File Drop Adapter
├── Database Adapter
├── Barcode Adapter
├── Balance Adapter
└── Vendor-Specific Plugin
```

## 27.3 Required sub-functionalities

- device registry;
- certificate/device identity;
- protocol configuration;
- tag/field mapping;
- connection health;
- polling/subscription;
- source timestamp;
- receive timestamp;
- sequence number;
- unit mapping;
- data-quality code;
- validation;
- local durable buffer;
- encryption;
- retry;
- deduplication;
- ordered delivery;
- acknowledgement;
- configuration versioning;
- remote update control;
- local diagnostics;
- time-sync health;
- evidence hashing.

## 27.4 Buffer design

Recommended local store:

- SQLite or equivalent embedded transactional store;
- WAL/durable mode;
- application-level encrypted payloads or validated encrypted volume;
- append-oriented event queue;
- maximum retention configurable.

Edge buffer is not the long-term regulatory archive.

## 27.5 Device data command/event separation

Read-only evidence path and equipment command/control path shall be separated.

V1 shall default to **read/capture first**.

Any future command to equipment requires a dedicated safety/security specification.

---

# 28. IDENTITY ARCHITECTURE

## 28.1 Identity layers

```text
Customer Identity
   Entra / Okta / AD / Other
            │
            ▼
Keycloak-compatible Broker / Identity Boundary
            │
       OIDC / SAML
            ▼
Frappe + GxP Services
```

## 28.2 Identity types

- human user;
- service account;
- integration account;
- Edge Gateway;
- instrument/device;
- CI/CD deployer;
- break-glass administrator.

They shall never be conflated.

## 28.3 Required controls

- unique subject identifier;
- display name/history;
- site scope;
- role assignment;
- qualification link;
- MFA policy;
- step-up policy;
- session expiry;
- account disablement;
- emergency access;
- service-account secrets/certificates;
- periodic access review;
- privileged-role review.

---

# 29. SEGREGATION OF DUTIES

The Authorization Service shall support configurable constraints including:

- performer != verifier;
- author != approver;
- production operator != independent QA release where configured;
- application admin cannot create user signatures;
- DB admin cannot perform product release;
- security admin cannot modify batch data;
- emergency-access use requires independent review;
- vendor support access is time-limited and approved.

Every SoD denial shall have a reason code usable in validation evidence.

---

# 30. EVENT ARCHITECTURE

## 30.1 Event pattern

```text
Authoritative PostgreSQL Transaction
        │
        ├── Domain state
        ├── Audit event
        └── Outbox row
                 │
                 ▼
          Outbox Publisher
                 │
                 ▼
           Event Bus
                 │
       ┌─────────┼──────────┐
       ▼         ▼          ▼
   Frappe     ERP/LIMS   Analytics/
 Projection   Adapter    Notification
```

## 30.2 Event bus rule

The event bus is transport, **not regulatory truth**.

If an event is lost from the bus, it must be reproducible from the outbox/domain record.

## 30.3 Event envelope

```json
{
  "event_id": "uuid",
  "event_type": "BatchStepCompleted",
  "schema_version": "1.0",
  "tenant_id": "...",
  "site_id": "...",
  "aggregate_id": "...",
  "aggregate_version": 45,
  "occurred_at_utc": "...",
  "correlation_id": "...",
  "causation_id": "...",
  "payload": {}
}
```

## 30.4 Schema governance

- backward compatibility rules;
- schema registry/repository;
- consumer contract tests;
- versioned events;
- deprecation period;
- no silent field semantic change.

---

# 31. API ARCHITECTURE

## 31.1 API styles

- REST for commands/query;
- OpenAPI specifications;
- JSON Schema for regulated payloads;
- webhook/callback where needed;
- asynchronous events for integration;
- no public direct database access.

## 31.2 Critical API controls

Every regulated mutation endpoint requires:

- authenticated identity;
- authorization scope;
- tenant/site context;
- expected version;
- idempotency key;
- request ID;
- validation;
- response record/version ID;
- audit event.

## 31.3 Service-to-service security

Use:

- mTLS where practical;
- OAuth2 client credentials or equivalent workload identity;
- short-lived credentials;
- scoped service identities;
- secret rotation;
- no hard-coded secrets.

---

# 32. DATA MODEL OWNERSHIP MATRIX

| Data domain | Authoritative system |
|---|---|
| UI preferences | Frappe |
| Draft configuration | Frappe until release |
| Released recipe | GxP Record Vault |
| Released specification | GxP Record Vault |
| Batch snapshot | GxP Core |
| Batch step state/result | GxP Core |
| Regulated signature | GxP Signature Service |
| Audit trail | GxP Audit Ledger |
| Genealogy | GxP Genealogy Service |
| Quality-event authoritative state | GxP/QMS Core |
| Material regulated status | GxP Material Service |
| Financial inventory valuation | ERP when external |
| Commercial AP/GL | ERP |
| QC basic result | GxP QC |
| External LIMS result | LIMS source + immutable accepted GxP result version |
| Raw high-frequency equipment data | Historian/evidence store |
| Relevant equipment evidence | GxP Evidence Service |
| Identity credential | Customer IdP/Keycloak |
| Training/qualification state | Controlled training/qualification service |
| Evidence files | Object/evidence storage + GxP manifest |

---

# 33. FILE / EVIDENCE ARCHITECTURE

## 33.1 Evidence types

- PDF;
- image;
- COA;
- machine file;
- CSV;
- instrument report;
- certificate;
- calibration evidence;
- sterilization report;
- environmental report;
- signed export.

## 33.2 Evidence manifest

Every regulated evidence object shall have:

```text
evidence_id
file_name
media_type
size
sha256
source
source_record
created_at
received_at
uploaded_by/source_identity
storage_location
retention_class
encryption_metadata
malware_scan_status
version
```

## 33.3 Storage

Use an abstraction supporting:

- AWS S3;
- Azure Blob;
- on-prem S3-compatible/object storage.

Released evidence should support immutability/WORM retention where deployment infrastructure provides it.

Application DB stores references and hashes, not giant binary payloads.

---

# 34. TIME ARCHITECTURE

Regulated event time shall use controlled server-side UTC.

## 34.1 Store

- authoritative UTC timestamp;
- original device/source timestamp where applicable;
- local timezone identifier;
- receive timestamp;
- clock-quality metadata for Edge/device sources.

## 34.2 Controls

- NTP/time-sync monitoring;
- clock drift alarm;
- no browser-supplied authoritative time;
- DST only affects display, not stored chronology;
- Edge queues retain original source time + sequence.

---

# 35. Frappe ↔ GxP PROJECTION MODEL

Frappe shall display GxP data through one of:

- service API;
- controlled synchronized projection;
- Virtual DocType/external-backed view where appropriate.

Projection rows shall contain:

- GxP record ID;
- GxP version;
- projection update time;
- projection status.

If projection version < authoritative version, UI shall indicate stale/read-sync status rather than presenting stale content as authoritative.

---

# 36. CUSTOMER CONFIGURATION ARCHITECTURE

## 36.1 Allowed configuration

- sites;
- rooms/areas/lines;
- users;
- approved role mappings;
- products;
- materials;
- equipment;
- recipes;
- specifications;
- limits;
- sampling plans;
- signature requirements within supported policy model;
- notification routing;
- approved workflow/profile options.

## 36.2 Controlled configuration

Changes affecting GxP behavior require:

- draft;
- reason/change control as applicable;
- impact assessment;
- approval/signature;
- version;
- effective date;
- immutable released version;
- training/revalidation impact where applicable.

## 36.3 Prohibited runtime customization

- arbitrary Python;
- arbitrary JavaScript changing compliance logic;
- direct SQL;
- unsupported Frappe server scripts;
- unsigned calculation scripts;
- production code patching;
- manual editing of released DB rows.

---

# 37. DDCP PROFILE ENGINE

The DDCP profile engine defines product-specific requirements without forking the core.

## 37.1 Profile dimensions

- constituent types;
- manufacturing route;
- sterile/aseptic applicability;
- lot vs serial tracking;
- UDI applicability;
- stability;
- reserve samples;
- device testing;
- environmental requirements;
- packaging/label controls;
- required QC;
- release approvals.

## 37.2 V1 reference profiles

### Profile A — Injectable Drug Delivery

Prefilled syringe, autoinjector, insulin pen, cartridge + injector.

### Profile B — Inhalation Delivery

MDI/DPI/nasal/other applicable inhalation forms.

### Profile C — Drug-Eluting / Coated Device

Drug-coated/eluting stent, catheter, implant or related product.

Each receives a dedicated specification and validation delta.

---

# 38. RELEASE / DISPOSITION ENGINE

## 38.1 Inputs

The engine evaluates:

- all required steps complete;
- required signatures valid;
- QC complete;
- unresolved deviation status;
- unresolved OOS/OOT status;
- material reconciliation;
- yield;
- equipment qualification;
- personnel qualification;
- environmental/sterile evidence;
- label/packaging reconciliation;
- genealogy completeness;
- required documents/evidence;
- customer/product-specific release rules.

## 38.2 Outputs

- eligible for release;
- blocked with machine-readable reasons;
- hold;
- reject;
- rework/reprocess route;
- destruction;
- other configured controlled disposition.

## 38.3 Release action

Final release requires:

- current rule evaluation;
- current record version;
- required QA authorization;
- Part 11 step-up signature;
- release event;
- immutable release snapshot;
- export readiness.

---

# 39. REVIEW BY EXCEPTION ARCHITECTURE

## 39.1 Exception index

A batch exception index shall include:

- deviations;
- OOS;
- OOT;
- NCR;
- parameter excursions;
- manual entries replacing device data;
- manual overrides;
- late steps;
- expired/temporary qualifications;
- equipment exceptions;
- material exceptions;
- environmental excursions;
- corrected values;
- missing signatures;
- failed integration;
- missing evidence;
- reconciliation variance;
- yield variance;
- rule warnings.

## 39.2 QA review screen

The UI should prioritize:

1. batch overview;
2. exception severity;
3. affected step/material/equipment;
4. evidence;
5. audit trail;
6. resolution;
7. unresolved blockers;
8. final release eligibility.

---

# 40. ERP ADAPTER ARCHITECTURE

## 40.1 Provider interfaces

```text
ItemProvider
SupplierProvider
ProcurementProvider
InventoryProvider
WarehouseProvider
ManufacturingProvider
FinancialReferenceProvider
```

## 40.2 Adapter implementations

- Native;
- ERPNext;
- SAP;
- Oracle;
- Dynamics;
- custom ERP.

## 40.3 Rules

- no ERP-specific code inside batch domain;
- mapping tables are versioned;
- integration errors visible;
- retries idempotent;
- financial fields do not become GxP truth unless explicitly configured;
- GxP consumption evidence remains independently retrievable.

---

# 41. LIMS ADAPTER ARCHITECTURE

Provider interface shall abstract vendor behavior.

Implementations may include:

- native basic QC;
- LabWare;
- STARLIMS;
- openBIS;
- customer LIMS.

No LIMS adapter may directly release a batch.

It may submit evidence/results; the Release Engine determines eligibility.

---

# 42. SECURITY ARCHITECTURE

## 42.1 Authentication

- SSO via OIDC/SAML;
- MFA policy;
- regulated signature step-up;
- no shared accounts;
- workload identities;
- device certificates.

## 42.2 Authorization

- RBAC;
- resource/site scope;
- qualification;
- SoD;
- contextual policy;
- least privilege.

## 42.3 Network

- TLS;
- private DB subnets;
- restricted east-west paths;
- ingress/API gateway;
- egress controls;
- Edge mTLS.

## 42.4 Secrets

- cloud secret manager or on-prem vault abstraction;
- rotation;
- no secrets in repository;
- no secrets in container images;
- no passwords in logs.

## 42.5 Encryption

- TLS in transit;
- encryption at rest;
- backup encryption;
- object-storage encryption;
- managed keys;
- optional customer-managed keys.

## 42.6 Application security

- input validation;
- CSRF;
- XSS controls;
- output encoding;
- SQL parameterization;
- upload scanning;
- content-type validation;
- rate limiting;
- authorization tests;
- anti-replay;
- idempotency;
- dependency scanning.

---

# 43. PRIVILEGED ACCESS

Privileged access must be treated separately from normal application roles.

## 43.1 Admin categories

- application admin;
- identity admin;
- security admin;
- database admin;
- infrastructure admin;
- vendor support.

## 43.2 Controls

- MFA;
- time-limited access where possible;
- approval for production access;
- session logging/audit;
- no direct content alteration;
- break-glass process;
- post-access review;
- customer notification/approval where contractually required.

Any direct database intervention affecting regulated data requires controlled incident/deviation/change handling and independent forensic evidence.

---

# 44. OBSERVABILITY

## 44.1 Signals

- application logs;
- security logs;
- metrics;
- traces;
- audit-health metrics;
- integration health;
- queue depth;
- Temporal workflow health;
- Edge buffer health;
- DB health;
- storage health;
- backup health.

## 44.2 Tooling principles

Use OpenTelemetry-compatible instrumentation.

Monitoring tools must not become a regulatory record source unless explicitly designed and validated.

## 44.3 Alert examples

- audit writer failure;
- signature service unavailable;
- NTP drift;
- DB replication lag;
- Edge buffer > threshold;
- failed ERP sync;
- LIMS result schema failure;
- backup failure;
- immutable storage failure;
- excessive failed login/signature attempts.

---

# 45. BACKUP, ARCHIVAL & DISASTER RECOVERY

## 45.1 Backup scope

- Frappe DB;
- GxP DB;
- identity configuration;
- Temporal persistence/configuration;
- object/evidence storage;
- deployment configuration;
- encryption-key metadata;
- integration mappings.

## 45.2 Backup controls

- encrypted;
- access controlled;
- off-site/cross-region where required;
- immutable copy where practical;
- retention policy;
- restore tests;
- backup-job monitoring.

## 45.3 RPO/RTO baseline targets

Final contract targets are customer-specific.

Architecture target:

| Component | Target design intent |
|---|---|
| GxP DB | low RPO through managed replication/WAL strategy |
| Evidence storage | durable replicated object storage |
| Edge buffer | retains local source events during central outage |
| Frappe projection | rebuildable from GxP/events where designed |
| Audit | protected as critical data |

Exact RPO/RTO values shall be frozen in deployment/SLA specifications, not assumed from this document.

---

# 46. HIGH AVAILABILITY

For enterprise deployment, architecture shall permit:

- multiple application replicas;
- multiple GxP API replicas;
- HA PostgreSQL;
- HA MariaDB where required;
- redundant ingress/load balancing;
- multiple Temporal workers;
- durable event infrastructure;
- redundant object storage;
- Edge retry/buffering.

No regulated correctness assumption may depend on a single web-process memory state.

---

# 47. SCALE TARGETS

Frozen design target from Document 01:

| Dimension | Target |
|---|---:|
| Plants/customer | 10+ supported architecture |
| Concurrent users/plant | 50 |
| Concurrent users/customer | 250+ |
| Batches/day/plant | 50+ |
| Steps/batch | 1,000 normal; several thousand supported |
| Equipment sources/site | hundreds |
| Audit events | architecture should tolerate millions/day without redesign |
| Retention | 10+ year capable / configurable |
| Serialized records | high-volume lot/serial genealogy |

## 47.1 Scaling rules

- stateless APIs scale horizontally;
- DB indexes/partitioning planned by tenant/site/date where beneficial;
- audit partitions by time/tenant;
- event consumers horizontally scalable;
- large exports asynchronous;
- telemetry excluded from OLTP where possible;
- genealogy query indexes required;
- batch execution queries optimized by active-batch partitions/read models.

---

# 48. FRONT-END / UX ARCHITECTURE

## 48.1 User experiences

Separate optimized workspaces for:

- operator;
- dispensing;
- warehouse;
- production supervisor;
- QA;
- QC;
- engineering;
- admin;
- auditor.

## 48.2 Production execution UX

Production execution shall prioritize:

- large clear step instructions;
- current step only;
- material/equipment verification;
- scanner/device input;
- target/actual display;
- immediate limit feedback;
- required reason/signature;
- clear hold/exception state;
- minimal navigation.

A dedicated Vue/Frappe-UI-based production execution interface may be used while remaining within the Frappe application shell.

## 48.3 Accessibility

Architecture shall support:

- keyboard operation;
- clear validation feedback;
- non-color-only status indication;
- scalable text;
- accessible form labels.

---

# 49. REGULATORY EXPORT SERVICE

## 49.1 Output

- human-readable PDF;
- structured JSON/XML where configured;
- audit trail;
- signature manifest;
- attachment manifest;
- machine evidence manifest;
- checksums;
- export manifest.

## 49.2 Export generation

Export is generated from authoritative GxP records, not from mutable UI state.

Each export stores:

- export ID;
- record/version;
- generation time;
- generator version;
- file hashes;
- included evidence versions.

---

# 50. VALIDATION / CSA ARCHITECTURE

## 50.1 Traceability model

Every requirement has a stable ID.

```text
Document 01 Requirement
      ↓
Document 02 Architecture Control
      ↓
Detailed Module Requirement
      ↓
Code Component
      ↓
Automated / Manual Test
      ↓
Release Evidence
```

## 50.2 Repository traceability

Recommended metadata:

```text
Requirement ID
Risk ID
Test ID
Commit / PR
Release version
Validation status
```

## 50.3 Risk-based testing

Higher assurance for:

- signatures;
- audit;
- record locking;
- recipe release;
- batch execution;
- calculations;
- genealogy;
- material eligibility;
- QA release;
- data migration;
- backup/restore;
- integration result acceptance.

## 50.4 Test classes

- unit;
- property/rule tests;
- API;
- contract;
- workflow replay;
- integration;
- database migration;
- security;
- concurrency;
- idempotency;
- failure/recovery;
- audit-integrity;
- signature;
- negative;
- performance;
- backup/restore;
- DR;
- validation scenario.

---

# 51. DATA MIGRATION ARCHITECTURE

Customer onboarding may require migration of:

- products;
- materials;
- suppliers;
- equipment;
- users/roles;
- training;
- recipes;
- specifications;
- open inventory;
- historical batches;
- documents.

## 51.1 Migration controls

- approved mapping;
- source evidence;
- extraction checksum;
- transformation rules;
- exception report;
- load validation;
- record counts;
- reconciliation;
- migrated-record provenance;
- migration version;
- approval/sign-off.

Historical data shall be distinguishable from records created natively in the new platform.

---

# 52. SOFTWARE SUPPLY CHAIN

## 52.1 Required controls

- SBOM;
- dependency lock files;
- exact version pinning;
- license register;
- vulnerability scanning;
- signed release artifacts;
- image digest pinning;
- provenance/attestation where supported;
- third-party approval;
- controlled dependency upgrade.

## 52.2 Preferred third-party components

| Component | Role | License strategy |
|---|---|---|
| Frappe | application framework | MIT |
| Keycloak | identity | Apache-2.0 |
| Temporal | workflow | MIT |
| PostgreSQL | GxP DB | permissive PostgreSQL license |
| NATS | event transport | Apache-2.0 |
| Kubernetes | orchestration | Apache-2.0 |
| OpenTelemetry | observability | Apache-2.0 |

MariaDB is used as Frappe operational infrastructure initially and must remain in the third-party license register. Exact distribution obligations shall be reviewed before packaged/on-prem distribution.

Every dependency license is verified at the exact pinned version/commit.

---

# 53. REPOSITORY ARCHITECTURE

Recommended monorepo or tightly coordinated repositories:

```text
ebmr-platform/
│
├── apps/
│   └── ebmr_frappe/
│
├── services/
│   ├── gxp-api/
│   ├── signature/
│   ├── audit/
│   ├── execution/
│   ├── genealogy/
│   ├── quality/
│   └── integration/
│
├── edge/
│   └── gateway/
│
├── connectors/
│   ├── erpnext/
│   ├── sap/
│   ├── oracle/
│   ├── dynamics/
│   └── lims/
│
├── contracts/
│   ├── openapi/
│   ├── json-schema/
│   └── events/
│
├── packages/
│   ├── shared-types/
│   ├── canonicalization/
│   ├── rule-sdk/
│   └── test-fixtures/
│
├── infrastructure/
│   ├── kubernetes/
│   ├── helm/
│   ├── aws/
│   ├── azure/
│   └── onprem/
│
├── validation/
│   ├── requirements/
│   ├── risk/
│   ├── traceability/
│   ├── tests/
│   ├── evidence/
│   └── releases/
│
├── docs/
│   ├── architecture/
│   ├── adr/
│   ├── api/
│   └── operations/
│
└── security/
    ├── threat-model/
    ├── sbom/
    └── license-register/
```

Logical separation may be implemented using multiple Git repositories if customer/security policy requires it.

---

# 54. BRANCH / RELEASE MODEL

Recommended:

```text
main
  └── protected, releasable

feature/*
fix/*
security/*
release/*
hotfix/*
```

Rules:

- no direct push to main;
- mandatory PR;
- required review;
- automated tests;
- security checks;
- migration checks;
- traceability metadata;
- release tag;
- signed artifact;
- release evidence archive.

---

# 55. DATABASE MIGRATION RULES

Regulated database migrations require:

- forward migration;
- rollback or recovery strategy;
- test on representative data;
- data-loss assessment;
- migration checksum;
- release linkage;
- before/after reconciliation;
- production backup before high-risk change.

A migration shall never silently delete regulated historical data.

---

# 56. CI/CD ARCHITECTURE

Pipeline stages:

```text
Source
 ↓
Lint / Typecheck
 ↓
Unit Tests
 ↓
SAST / Secret Scan
 ↓
Dependency / License Scan
 ↓
Build
 ↓
SBOM
 ↓
Container Scan
 ↓
Integration Tests
 ↓
GxP Critical Tests
 ↓
Migration Tests
 ↓
Package / Sign
 ↓
Validation Evidence
 ↓
Approved Deployment
```

Production deployment requires authorized release approval.

---

# 57. ENVIRONMENTS

Minimum:

- developer;
- integration;
- validation/test;
- staging/pre-production;
- production.

Rules:

- production data is not copied casually into development;
- sanitized datasets used outside controlled production;
- configuration differences are documented;
- validation environment mirrors critical production topology sufficiently for intended testing.

---

# 58. CONFIGURATION & SECRET SEPARATION

Configuration categories:

### Code configuration

Version controlled.

### Customer configuration

Stored as controlled records with audit/version where GxP relevant.

### Secrets

External secret manager only.

### Infrastructure configuration

Infrastructure-as-code, reviewed and versioned.

---

# 59. AI ARCHITECTURE — V1

## 59.1 Allowed advisory functions

- batch review assistance;
- exception summarization;
- deviation summarization;
- SOP/document retrieval;
- historical similarity;
- quality trend insight;
- anomaly detection;
- natural-language search.

## 59.2 Prohibited autonomous actions

AI cannot independently:

- sign;
- release;
- approve;
- reject;
- change released recipe;
- change specification;
- delete/supersede evidence;
- close CAPA/deviation;
- alter audit trail;
- execute equipment control commands.

## 59.3 AI gateway

All AI access shall use a controlled service that:

- enforces authorization;
- filters data by tenant/site/role;
- logs request context;
- records model/version where required;
- prevents tool access outside scope;
- routes proposed regulated actions through normal GxP Mutation Gateway.

---

# 60. THREAT MODEL — PRIMARY CONCERNS

Document 02 identifies these high-priority threats for SPEC-SEC-001:

1. compromised operator account;
2. compromised QA account;
3. malicious/overprivileged administrator;
4. direct database manipulation;
5. audit tampering;
6. signature replay;
7. stale record signing;
8. API replay/duplicate command;
9. cross-tenant data exposure;
10. malicious file upload;
11. compromised integration account;
12. fake equipment/device source;
13. Edge data alteration;
14. clock manipulation;
15. dependency compromise;
16. CI/CD compromise;
17. secret leakage;
18. ransomware/destructive admin action;
19. backup corruption;
20. unauthorized production customization.

---

# 61. SECURITY CONTROL MAPPING

| Threat | Architectural control |
|---|---|
| Account compromise | MFA, step-up, least privilege, session controls |
| Signature replay | nonce, expiry, record hash binding |
| Direct DB manipulation | network restriction, DB roles, audit/monitoring, app-only mutation |
| Audit modification | append-only design, hash integrity, WORM checkpoints |
| Duplicate API action | idempotency key |
| Stale write | expected version / optimistic concurrency |
| Cross-tenant exposure | dedicated deployments + tenant assertions |
| Fake device | mTLS/device identity |
| Edge replay | sequence/idempotency/source signature |
| Time manipulation | NTP monitoring + server receive time |
| Malicious dependency | SBOM, scanning, signed build |
| Admin abuse | privileged-access controls and independent monitoring |

---

# 62. INCIDENT / DEVIATION INTERFACE

Security or system incidents affecting regulated records shall be able to create/link:

- IT incident;
- deviation;
- impact assessment;
- affected batches;
- affected records;
- CAPA;
- corrective release;
- customer notification evidence.

Technical observability must support investigation without altering the original GxP record.

---

# 63. PERFORMANCE & CONCURRENCY CONTROLS

Critical concurrency examples:

- two users attempting same step;
- two users selecting same material quantity;
- duplicate scanner submission;
- repeat Edge event;
- simultaneous QA actions;
- retrying ERP callback.

Controls:

- optimistic record version;
- database unique constraints;
- idempotency key;
- advisory/row locks where necessary;
- reservation records;
- deterministic conflict responses;
- audit of rejected conflict where significant.

---

# 64. FAILURE MODE RULES

## 64.1 GxP DB unavailable

- no regulated mutation succeeds;
- UI becomes read-only/degraded where safe;
- no fake success state;
- Edge continues buffering.

## 64.2 Frappe unavailable

- GxP data remains intact;
- production UI unavailable unless alternate client is provided;
- no data corruption.

## 64.3 Event bus unavailable

- authoritative transaction continues if outbox commit succeeds;
- outbox queues;
- integrations become delayed;
- alert generated.

## 64.4 ERP unavailable

- behavior depends on transaction type;
- regulated execution may continue only where configured and material truth is safely known;
- ERP sync marked pending;
- no silent loss.

## 64.5 LIMS unavailable

- required test result remains pending;
- release blocked where required;
- no fabricated pass.

## 64.6 IdP unavailable

- existing authenticated session may permit non-signature actions per security policy;
- new regulated signatures requiring step-up cannot complete;
- no signature bypass.

---

# 65. TECHNICAL DOCUMENTATION GENERATED FROM DOCUMENT 02

Document 02 creates the architecture base for:

- SPEC-GXP-001 GxP Mutation Gateway
- SPEC-GXP-002 Part 11 Electronic Signature
- SPEC-GXP-003 Audit Ledger
- SPEC-GXP-004 Record Version Vault
- SPEC-EBMR-001 Recipe / Master Manufacturing
- SPEC-EBMR-002 Batch Execution
- SPEC-EBMR-003 Review & Release
- SPEC-EBMR-004 Genealogy
- SPEC-MAT-001 Procurement/Supplier Quality
- SPEC-MAT-002 Inventory/Dispensing/Reconciliation
- SPEC-QC-001 QC/LIMS
- SPEC-QMS-001 Deviation
- SPEC-QMS-002 CAPA
- SPEC-QMS-003 OOS/OOT
- SPEC-QMS-004 Change Control
- SPEC-QMS-005 Document Control
- SPEC-QMS-006 Training/Qualification
- SPEC-QMS-007 Complaint/Postmarket/Recall
- SPEC-QMS-008 Risk
- SPEC-EQP-001 Equipment
- SPEC-ASEPTIC-001 Sterile/Aseptic
- SPEC-EDGE-001 Edge Gateway
- SPEC-IAM-001 Identity/Authorization/SoD
- SPEC-INT-001 ERP
- SPEC-INT-002 LIMS
- SPEC-SEC-001 Security/Threat Model
- SPEC-VAL-001 Validation
- SPEC-DDCP-A Injectable Profile
- SPEC-DDCP-B Inhalation Profile
- SPEC-DDCP-C Drug-Eluting/Coated Profile

---

# 66. IMPLEMENTATION PHASES

## Phase 0 — Engineering foundation

- repository;
- CI/CD;
- SBOM/license register;
- Frappe baseline;
- GxP service skeleton;
- PostgreSQL;
- identity;
- OpenAPI/contracts;
- test framework;
- observability.

## Phase 1 — GxP trust core

- mutation gateway;
- authorization;
- signature;
- audit;
- record vault;
- canonicalization/hash;
- outbox/event model.

**No eBMR production implementation should bypass this phase.**

## Phase 2 — Master & execution core

- product/material/equipment masters;
- recipe;
- released version;
- batch snapshot;
- execution state machine;
- Temporal orchestration;
- qualification/equipment/material eligibility.

## Phase 3 — Material/QC

- procurement/material;
- quarantine/release;
- dispensing;
- reconciliation;
- basic QC;
- LIMS adapter.

## Phase 4 — Quality

- deviation;
- OOS/OOT;
- CAPA;
- NCR;
- change control;
- training;
- supplier quality.

## Phase 5 — DDCP

- combination genealogy;
- eDHR;
- packaging/label;
- postmarket/complaint;
- reference manufacturing profiles.

## Phase 6 — Sterile/Edge/Integration

- Edge Gateway;
- sterile data;
- equipment integration;
- ERP connectors;
- advanced LIMS.

## Phase 7 — Review/Release/Validation

- review by exception;
- release engine;
- regulatory export;
- complete validation package;
- performance/security/DR qualification.

---

# 67. CLAUDE CODE / CODEX — NON-NEGOTIABLE ENGINEERING RULES

These rules shall be included in repository agent instructions.

## 67.1 Never do

- never edit Frappe framework core;
- never edit ERPNext core for product behavior;
- never write regulated data directly from UI to MariaDB as authoritative truth;
- never bypass Mutation Gateway;
- never bypass signature challenge;
- never manually create a signature;
- never UPDATE/DELETE audit ledger rows;
- never overwrite a released recipe/specification;
- never overwrite original QC/OOS evidence;
- never trust browser timestamp;
- never trust client-provided user ID;
- never add arbitrary executable customer scripts to GxP logic;
- never hardcode SAP/ERPNext/LIMS vendor behavior into domain core;
- never store secrets in source;
- never disable authorization to make tests pass;
- never add a dependency without license/SBOM update;
- never change DB schema without migration;
- never silently change event/API semantics;
- never generate a release without traceable tests.

## 67.2 Always do

- use stable requirement IDs;
- add tests for regulated rule changes;
- use idempotency for mutation/integration operations;
- use expected-version concurrency checks;
- preserve originals;
- record reasons where required;
- use server-side policy checks;
- log correlation IDs;
- use explicit domain errors;
- update OpenAPI/schema contracts;
- update migration scripts;
- update SBOM/license register;
- add/adjust traceability;
- preserve backward-compatible data reading where required;
- document validation impact.

---

# 68. CODING BOUNDARIES

## Frappe code may

- build forms/workspaces;
- maintain drafts/configuration;
- call GxP APIs;
- display projections;
- generate non-authoritative UI summaries.

## Frappe code may not

- finalize regulated state without GxP API;
- create valid regulated signatures itself;
- change released records;
- delete audit history.

## GxP code must

- be framework-independent enough to expose stable APIs;
- enforce rules server-side;
- own regulated transaction semantics;
- expose testable domain services.

---

# 69. ACCEPTANCE CRITERIA FOR ARCHITECTURE IMPLEMENTATION

An implementation conforms to Document 02 only if:

1. all regulated mutations flow through GxP Core;
2. released recipes live in immutable GxP version model;
3. electronic signatures are challenge-based and record-bound;
4. audit records are independent and append-only;
5. Frappe DB failure cannot destroy authoritative GxP history;
6. generic Frappe CRUD cannot modify released records;
7. integrations use adapter interfaces;
8. Edge data is attributable to a registered source;
9. all critical actions have server-side authorization;
10. batch release is produced by Release Engine + authorized e-signature;
11. customer configuration cannot inject uncontrolled GxP code;
12. regulated records can be exported with signature/audit/evidence manifests;
13. requirements and tests remain traceable;
14. dependency/license records exist;
15. backup/restore and failure scenarios are testable.

---

# 70. ARCHITECTURE FREEZE DECLARATION

The following technical architecture is frozen as the baseline for detailed specifications:

- Frappe as primary application framework;
- MariaDB as initial Frappe operational DB;
- PostgreSQL as authoritative GxP DB;
- TypeScript/Node.js for proprietary GxP services and Edge;
- Keycloak-compatible/customer SSO identity boundary;
- mandatory step-up authentication for regulated signatures;
- proprietary Signature Service;
- proprietary Audit Ledger;
- proprietary Record Version Vault;
- proprietary Mutation Gateway;
- proprietary Rules/Policy layer;
- Temporal for durable orchestration, but not regulatory record truth;
- transactional outbox/event-driven projections;
- NATS-compatible event transport recommended;
- S3-compatible evidence storage abstraction;
- regulated integration through adapters;
- no fully disconnected Part 11 browser execution in V1;
- dedicated enterprise customer deployment model;
- cloud-neutral containers/Kubernetes with AWS and Azure references;
- advisory-only AI;
- no uncontrolled runtime customization;
- no direct mutation of released regulated records.

Changes to these architectural controls require an ADR/change-impact review.

---

# 71. NEXT DOCUMENTS

The recommended next specification sequence is:

1. **SPEC-GXP-001 — GxP Mutation Gateway**
2. **SPEC-GXP-002 — Part 11 Electronic Signature**
3. **SPEC-GXP-003 — Immutable Audit Ledger**
4. **SPEC-GXP-004 — Record Version Vault & Controlled Corrections**
5. **SPEC-EBMR-001 — Recipe / Master Manufacturing Record**
6. **SPEC-EBMR-002 — Batch Execution & State Machine**
7. **SPEC-IAM-001 — Identity / Authorization / SoD**
8. **SPEC-EBMR-004 — Genealogy & Traceability**
9. **SPEC-MAT-001 / 002 — Procurement, Inventory, Dispensing**
10. **SPEC-QC-001 — QC/LIMS**
11. QMS specifications
12. Sterile/Edge/ERP/LIMS specifications
13. DDCP reference manufacturing profiles
14. Security and validation packages

The first four GxP specifications should be frozen before large-scale eBMR functionality is implemented because every downstream regulated feature depends on them.

---

# 72. REGULATORY / VALIDATION QUALIFICATION

This document is a technical architecture specification and not a legal declaration of FDA compliance.

Compliance depends on:

- the final implementation;
- intended use;
- customer procedures;
- product and constituent classification;
- manufacturing process;
- configuration;
- infrastructure;
- validation/CSA;
- operational controls;
- training;
- regulated-user behavior.

The final product and validation package should be reviewed by appropriately qualified US regulatory, quality and validation professionals before regulated production use.

---

# MASTER ARCHITECTURE PRINCIPLE

> **Frappe presents and configures the regulated manufacturing system.**  
> **The eBMR/eDHR domain layer understands manufacturing.**  
> **The GxP Core decides, records, signs and preserves regulated truth.**  
> **Temporal coordinates long-running work but never becomes regulatory truth.**  
> **Adapters connect ERP, LIMS and factory systems without contaminating the domain model.**  
> **Every regulated change remains attributable, authorized, versioned, auditable and recoverable.**
