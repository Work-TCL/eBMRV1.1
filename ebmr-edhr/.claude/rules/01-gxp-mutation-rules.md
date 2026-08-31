# Regulated mutation path

**Purpose:** Regulated mutation path for the eBMR/eDHR platform.
**Applicable paths/modules:** see `docs/generated/17_REPOSITORY_STRUCTURE.md`; this rule applies to every
service, the Frappe app, edge and integration code unless a narrower scope is stated below.
**Source documents:** Document 03 (SPEC-GXP-001), Document 11 (SPEC-EBMR-002), Document 101 (SPEC-ENG-005), Document 70 (SPEC-DATA-002)
**Source requirement IDs:** MUT-FR-001..032 (32); BAT-FR-001..036 (36); CTR-FR-001..036 (36); PG-FR-001..034 (34)

---

## Required implementation pattern

```ts
// every regulated command handler
async function handle(cmd: Command, ctx: AuthenticatedContext): Promise<MutationReceipt> {
  assertTenantSiteScope(cmd, ctx);                     // MUT-FR-003
  validateSchema(cmd);                                 // MUT-FR-005
  const decision = await policy.authorize(ctx, cmd);   // MUT-FR-006/007
  const sig = await signature.requireIfPolicy(cmd);    // MUT-FR-012/013 + Doc 106
  return db.transaction(async tx => {                  // MUT-FR-015
    const agg = await repo.loadForUpdate(tx, cmd.aggregate_id, cmd.expected_version); // MUT-FR-009
    assertTransitionAllowed(agg.state, cmd);           // MUT-FR-008
    const rules = await rulesEngine.evaluate(agg, cmd);// MUT-FR-014
    const next = apply(agg, cmd, rules);
    await repo.save(tx, next);                         // version++
    await vault.writeVersion(tx, next);                // Doc 06
    await audit.append(tx, auditEvent(cmd, agg, next, sig, decision)); // MUT-FR-016
    await outbox.append(tx, domainEvent(next));        // MUT-FR-018
    return receipt(next, sig);                         // MUT-FR-019
  });
}
```

## Forbidden patterns

- external I/O (HTTP, bus publish, file write) inside the transaction
- commit without an audit event and an outbox row
- accepting actor identity from the payload
- generic CRUD endpoints on regulated records
- degraded-mode commit when policy, signature or the authoritative DB is unavailable

## Required tests

unauthorized user; wrong site; expired qualification; invalid transition; stale version; duplicate click;
duplicate integration callback; missing reason; missing signature; record changed after challenge;
signature service outage; DB rollback; outbox publisher outage; projection outage; concurrent same-step
writes; replayed edge event; privileged repair command; schema backward compatibility; restart after commit.


## Source requirements (extract)

| ID | Requirement | Required behaviour |
|---|---|---|
| MUT-FR-001 | Single regulated mutation entry point | Every regulated create, modify, correct, approve, verify, release, reject, hold, resume, disposition, quality-state change and integration write shall enter through the GxP Mutation Gateway. Frappe ge |
| MUT-FR-002 | Authenticated actor context | Resolve human, service, integration or device identity from trusted server-side authentication context. Ignore client-supplied actor IDs/names for authority decisions. |
| MUT-FR-003 | Tenant/site scope enforcement | Resolve customer, legal entity, site and resource scope before business validation. Requests crossing tenant/site boundaries fail closed. |
| MUT-FR-004 | Command classification | Each mutation uses a versioned command type such as CompleteBatchStep, CorrectResult, ApproveDeviation, ReleaseBatch, UpdateMaterialStatus or AcceptLIMSResult. |
| MUT-FR-005 | Schema validation | Validate command envelope and payload against versioned JSON Schema/OpenAPI contract before domain processing. |
| MUT-FR-006 | Authorization decision | Call Policy/Authorization Service using subject, role, site, qualifications, resource state, requested action and SoD context. |
| MUT-FR-007 | Qualification/training gate | Where configured, confirm required current training, equipment qualification, area qualification or task competency before allowing action. |
| MUT-FR-008 | State-transition validation | Validate requested command against authoritative current state and allowed transition table; UI state is never authoritative. |
| MUT-FR-009 | Expected-version concurrency | Require expected aggregate/record version for mutations. Reject stale commands using optimistic concurrency. |
| MUT-FR-010 | Idempotency | Require idempotency key for commands capable of duplicate submission. Persist key, actor/source, command hash and resulting receipt. |
| MUT-FR-011 | Reason-for-change enforcement | Rules identify commands requiring controlled reason/comment. Reason is structured, required before commit and preserved in audit. |
| MUT-FR-012 | Signature requirement determination | Determine whether electronic signature is required, signature meaning, required signer class and whether one or multiple signatures are required. |
| MUT-FR-013 | Signature challenge integration | If signature is required, produce/consume a challenge bound to command, record ID, expected version/hash, meaning and expiry. Commit only after valid signature proof. |
| MUT-FR-014 | Domain-rule evaluation | Execute applicable released rule/calculation versions for materials, equipment, limits, eligibility, sequence, QMS and release controls. |
| MUT-FR-015 | Authoritative PostgreSQL transaction | Persist domain state, new version, audit event and outbox message in one PostgreSQL transaction. |
| MUT-FR-016 | Audit event creation | Create audit record with actor, UTC time, source, action, old/new representation or references, reason, signature, correlation and rule/software versions. |
| MUT-FR-017 | Record hash | Canonicalize resulting regulated record/version and calculate cryptographic digest where the record class requires integrity binding. |
| MUT-FR-018 | Transactional outbox | Write integration/domain event into outbox in the same transaction; external bus publishing occurs only after commit. |
| MUT-FR-019 | Mutation receipt | Return immutable identifiers: command ID, aggregate ID, resulting version, audit event ID, signature ID if applicable, correlation ID and record hash where applicable. |
| MUT-FR-020 | Projection update isolation | Frappe projection/read model updates occur asynchronously after authoritative commit and may be retried without altering regulatory truth. |
| MUT-FR-021 | Failure classification | Return stable machine-readable error codes for authentication, authorization, stale version, state violation, missing signature, rule failure, validation, dependency unavailable and system fault. |
| MUT-FR-022 | Fail closed for compliance dependencies | If authoritative DB, Signature Service for required signings, Policy Service or integrity-critical component is unavailable, mutation does not succeed. |
| MUT-FR-023 | Integration identity | ERP/LIMS/Edge commands use non-human identities with narrowly scoped permissions and source-system IDs. |
| MUT-FR-024 | Device/input source validation | For machine-originated mutations/evidence, verify registered source/device identity and mapping before acceptance. |
| MUT-FR-025 | Late/replayed command control | Detect timestamp/sequence anomalies and duplicate/replayed integration/device commands using source event IDs, sequences and idempotency. |
| MUT-FR-026 | Controlled administrative mutation | Exceptional admin/data-repair actions require dedicated privileged command types, incident/change/deviation reference, stronger authorization and independent review. |
| MUT-FR-027 | Correlation/causation | Every command and generated event carries request, correlation and causation identifiers across services and adapters. |
| MUT-FR-028 | Command retention | Retain sufficient command/receipt metadata for investigation, duplicate detection and validation evidence according to record class. |
| MUT-FR-029 | No arbitrary execution | Command handlers shall call validated domain services; customer-provided Python/JavaScript is prohibited in authoritative mutation execution. |
| MUT-FR-030 | Schema/version compatibility | Command handlers explicitly support/deprecate schema versions; semantic changes require new version and migration/compatibility assessment. |
| MUT-FR-031 | Security-event interface | Repeated denied, replayed, malformed, privilege-escalation or suspicious mutations generate security monitoring events separate from GxP audit where appropriate. |
| MUT-FR-032 | Inspection/reconciliation support | Provide query by command ID/correlation ID/record to trace command → decision → signature → version → audit → outbox. |
| BAT-FR-001 | Batch creation | Create batch from effective product + recipe version, site, target quantity and allowed production order/reference. |
| BAT-FR-002 | Unique identity | Assign immutable batch ID plus controlled human batch number. Prevent duplicate/reused business numbers by tenant/site policy. |
| BAT-FR-003 | Issue snapshot | At issue, create immutable execution snapshot from exact released dependencies. |
| BAT-FR-004 | Batch lifecycle | Authoritative states: Planned, Created/Snapshot Locked, Issued, Ready, In Execution, On Hold, Exception Pending, Production Complete, QA Review, Released/Rejected/Other Disposition, Closed. |
| BAT-FR-005 | Step instance creation | Instantiate executable step instances from snapshot with stable recipe step reference and batch-specific state. |
| BAT-FR-006 | Step readiness | Compute readiness from predecessors, conditions, material/equipment/personnel requirements, holds and quality blockers. |
| BAT-FR-007 | Step claim/start | Authorized operator may claim/start ready step; record operator, area, equipment context and start time. |
| BAT-FR-008 | Concurrent execution | Support parallel independent steps with version/concurrency protection and explicit join conditions. |

## SPEC_GAP triggers

Raise a SPEC_GAP rather than deciding, if you encounter: a missing signature/authorization/retention/
precision value, a conflict between two source documents, an entity without an owner, an event without a
producer, or any requirement that would need a regulated behaviour you cannot trace to
Document 03, Document 11, Document 101, Document 70 or Documents 106–115.
