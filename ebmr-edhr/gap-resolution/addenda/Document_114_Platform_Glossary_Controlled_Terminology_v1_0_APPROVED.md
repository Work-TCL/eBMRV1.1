# US eBMR / eDHR Regulated Manufacturing Platform
## Document 114 — Platform Glossary & Controlled Terminology — v1.0 APPROVED

**Specification ID:** SPEC-ENG-010
**Status:** APPROVED v1.0 (construction baseline) — approvers of record: Specification Owner
**Closes:** SG-017
**Approval:** Approved by the Project Owner during construction review on 2026-08-21. A formal Part 11 signature record must be captured in the QMS against this version before validated release; the approval block below is the record of the construction decision.

**Primary Dependencies:** Authoring Standard item 4; Documents 01–113

---

# 0. Why this document exists

The authoring standard requires terminology in every specification; none defines it. Several terms carry precise but different meanings across modules — "release" alone means recipe release, batch release, material release and software release. Terminology drift becomes implementation drift.

# 1. Rules

1. These definitions are binding across code, contracts, UI copy, tests and validation artefacts.
2. Where a term is ambiguous, the qualified form is mandatory: *recipe release*, *batch release*, *material release*, *software release*.
3. Prohibited loose synonyms: "approve" for "release", "log" for "audit event", "copy" for "projection", "delete" for "supersede", "user" for "subject" in policy contexts.
4. New domain terms are added here in the same change that introduces them.

# 2. Controlled terms

| Term | Definition | Owning document |
|---|---|---|
| **Aggregate** | The consistency boundary that owns a regulated entity and its version counter. All mutations to it go through its owning domain command. | Doc 03, Doc 70 |
| **Amendment** | A controlled change to a released record that creates a new version and preserves the original. Never an in-place edit. | Doc 06 |
| **Audit event** | The immutable record of a committed regulated mutation, written in the same transaction as the state change. | Doc 05 |
| **Authoritative store** | The single database or store that holds the truth for a regulated entity. Exactly one per entity. | Doc 69 |
| **Batch record release** | The QA decision to release a manufactured batch. Distinct from recipe release and from ERP document status. | Doc 15 |
| **Break-glass access** | Time-limited, reason-coded emergency privileged access, independently reviewed. Never an approval path. | Doc 63 |
| **Canonical form** | The deterministic structured representation of a record used for hashing and signature binding. | Doc 06 |
| **Challenge** | The server-side, single-use, expiring object that binds a signature ceremony to a record, version, hash and meaning. | Doc 04 |
| **Command** | A versioned, typed request to change regulated state, submitted through the Mutation Gateway. | Doc 03 |
| **Constituent** | A drug, biologic or device part of a combination product. | Doc 09, Docs 54–57 |
| **Correction** | A controlled change to previously recorded data, requiring reason-for-change and preserving the original value. | Doc 06 |
| **DDCP profile** | A released, versioned configuration that adds product-type-specific controls to the common execution platform. | Docs 54–57 |
| **Derived data** | Any projection, read model, cache, index or report built from authoritative data. Rebuildable, never regulatory truth. | Docs 71, 75 |
| **Disposition** | The quality decision on a batch, lot, material or nonconformance (release, reject, rework, destroy, further test). | Docs 15, 28 |
| **eDHR** | Electronic device history record: the production history of a device or device lot. | Doc 12 |
| **Evidence object** | An immutable, hash-addressed file or artefact referenced by a record's evidence manifest. | Doc 72 |
| **Expected version** | The aggregate version the caller believes it is acting on; the basis of optimistic concurrency. | Doc 03 |
| **Fail closed** | Refusing to commit when a compliance-critical dependency is unavailable, rather than degrading. | Doc 03 MUT-FR-022 |
| **Genealogy** | The traceability graph linking materials, batches, components, units and packaged product. | Doc 13 |
| **Idempotency key** | The value that lets a retried command return the original result without creating a second regulated event. | Doc 03 |
| **Independence** | The requirement that a signer or verifier is not the performer, author, or prior signer of the same record. | Docs 04, 107 |
| **Legal hold** | An authorized suspension of all disposal for a defined scope of records. | Doc 108 |
| **Line clearance** | The verified state that a line is free of previous product, materials and documents before a new batch. | Doc 39 |
| **Manifestation** | The human-readable display of a signature: printed name, UTC execution time and meaning. | Doc 04 SIG-FR-015 |
| **Master recipe / MMR** | The released manufacturing definition from which a batch is instantiated. | Doc 10 |
| **Meaning** | The controlled semantic of a signature: Performed, Verified, Reviewed, Approved, Released, Rejected, Authored, Witnessed. | Doc 04 SIG-FR-003 |
| **Mutation Gateway** | The single regulated write path: authorization, signature, rules, transaction, audit, outbox, receipt. | Doc 03 |
| **Outbox** | The table written in the same transaction as a state change, from which events are published after commit. | Doc 73 |
| **Periodic review** | The scheduled re-confirmation that a validated system remains in its validated state. | Doc 96 |
| **Projection** | A non-authoritative copy of regulated data maintained for UI or reporting, stamped with source id and version. | Doc 71 |
| **Qualification (personnel)** | A person's current training, competency, area or equipment authorization required before an action. | Doc 07 |
| **Qualification (system)** | IQ/OQ/PQ evidence that installed software and infrastructure perform as intended. | Docs 83–86 |
| **Reason for change** | The structured, mandatory justification recorded with corrections, overrides and controlled changes. | Doc 03 MUT-FR-011 |
| **Recipe release** | Approval of a master recipe version for use. Distinct from batch release. | Doc 10 |
| **Reconciliation (material)** | Comparing issued, consumed, returned, destroyed and remaining quantities against expectation. | Doc 22 |
| **Reconciliation (integration)** | Comparing GxP state with an external system's state and raising exceptions for differences. | Doc 53 |
| **Record class** | The classification that drives retention, signature policy, review and export behaviour for a record type. | Docs 106, 108 |
| **Record Version Vault** | The store of immutable released versions with canonical form, digest and evidence manifest. | Doc 06 |
| **Reportability** | The regulatory determination that an event must be reported, with its clock start and deadline. | Doc 59 |
| **Review by exception** | QA review focused on exceptions, corrections, overrides and out-of-limit events rather than every data point. | Doc 14 |
| **Safety case** | The surveillance-layer record referencing a source complaint/service/literature record for postmarket assessment. | Doc 58 |
| **Signature point** | An action for which the signature policy requires one or more electronic signatures. | Doc 106 |
| **SoD (segregation of duties)** | Standing role-pair prohibitions and per-action independence rules enforced by the policy engine. | Docs 07, 107 |
| **SPEC_GAP** | A recorded missing or conflicting regulated decision. The agent stops on affected scope rather than guessing. | Construction instruction §11 |
| **Step** | The unit of execution inside a batch, with its own state machine, results, evidence and signature requirements. | Doc 11 |
| **Store-and-forward** | Edge buffering of measurements when upstream connectivity is unavailable, with sequence and replay control. | Doc 45 |
| **Supersede** | Replacing a record version with a new version while preserving the original. The only permitted form of change to released data. | Doc 06 |
| **Tenant** | The customer boundary. Every regulated row is tenant-scoped and cross-tenant access fails closed. | Docs 66, 70 |
| **Traceability** | The demonstrable link from requirement to design, implementation, test and qualification evidence. | Doc 81 |
| **Validated state** | The condition in which the system, its configuration and its evidence remain within their approved validation baseline. | Doc 96 |
| **Work package** | A dependency-ordered implementation unit with its own scope, contracts, tests, acceptance gate and validation impact. | Construction instruction §20 |
| **WORM** | Write-once-read-many storage or retention lock applied to evidence objects. | Doc 72 |

# 3. Prohibited ambiguous usages

| Do not write | Write instead | Reason |
|---|---|---|
| "release the record" | "release the batch" / "release the recipe version" | Four distinct regulated meanings |
| "log the change" | "write the audit event" | Audit events are regulated records, logs are not |
| "sync the data" | "project the data" / "reconcile with ERP" | Projection and reconciliation are different controls |
| "delete the version" | "supersede the version" | Deletion of regulated data is prohibited |
| "the user signed off" | "the signer applied an `Approved` signature" | Signature meaning is controlled |
| "temporary override" | "approved exception with end date" | Overrides are controlled, bounded and signed |
| "auto-release" | "rule-evaluated release recommendation" | AI and rules never release autonomously |

# 4. Acceptance criteria

1. Glossary terms used consistently in generated code, contracts and artefacts.
2. Prohibited usages absent from UI copy and public contracts (lint check).
3. New terms added with their introducing change.

# 5. Approval block

| Role | Name | Decision | Date | Signature reference |
|---|---|---|---|---|
| Specification Owner |  |  |  |  |
