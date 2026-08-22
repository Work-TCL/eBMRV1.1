# WP-01 — Scope & Requirements

**In scope:** Documents 03, 04, 05, 06, 07, 08

## Document 03 — GxP Mutation Gateway (SPEC-GXP-001)

- Code location: `services/gxp-api/src/modules/mutation`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: MUT-FR-001..032 (32)

## Document 04 — 21 CFR Part 11 Electronic Signature (SPEC-GXP-002)

- Code location: `services/gxp-api/src/modules/signature`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: SIG-FR-001..030 (30)

## Document 05 — Immutable Audit Ledger & Audit Review (SPEC-GXP-003)

- Code location: `services/gxp-api/src/modules/audit`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: AUD-FR-001..030 (30)

## Document 06 — Record Version Vault, Locking, Amendment & Controlled Correction (SPEC-GXP-004)

- Code location: `services/gxp-api/src/modules/vault`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: VLT-FR-001..030 (30)

## Document 07 — Identity, Authorization, RBAC, Qualification & Segregation-of-Duties (SPEC-IAM-001)

- Code location: `services/gxp-api/src/modules/policy`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: IAM-FR-001..032 (32)

## Document 08 — Regulatory Rules & Calculation Engine (SPEC-GXP-006)

- Code location: `services/gxp-api/src/modules/rules`
- Authoritative store: PostgreSQL (GxP Core, authoritative)
- Risk class: **HIGHER-PROCESS-RISK**
- Requirements: RUL-FR-001..032 (32)

## All requirements

| ID | Doc | Requirement | Behaviour | Acceptance |
|---|---|---|---|---|
| MUT-FR-001 | 03 | Single regulated mutation entry point | Every regulated create, modify, correct, approve, verify, release, reject, hold, resume, disposition, quality-state change and integration write shall enter through the GxP Mutation Gateway. Frappe ge | Architectural tests prove no supported bypass path. |
| MUT-FR-002 | 03 | Authenticated actor context | Resolve human, service, integration or device identity from trusted server-side authentication context. Ignore client-supplied actor IDs/names for authority decisions. | Spoofed actor fields do not change attribution. |
| MUT-FR-003 | 03 | Tenant/site scope enforcement | Resolve customer, legal entity, site and resource scope before business validation. Requests crossing tenant/site boundaries fail closed. | Cross-site negative tests enforced. |
| MUT-FR-004 | 03 | Command classification | Each mutation uses a versioned command type such as CompleteBatchStep, CorrectResult, ApproveDeviation, ReleaseBatch, UpdateMaterialStatus or AcceptLIMSResult. | Unknown/unversioned commands rejected. |
| MUT-FR-005 | 03 | Schema validation | Validate command envelope and payload against versioned JSON Schema/OpenAPI contract before domain processing. | Malformed/additional prohibited fields rejected. |
| MUT-FR-006 | 03 | Authorization decision | Call Policy/Authorization Service using subject, role, site, qualifications, resource state, requested action and SoD context. | Every regulated command has explicit allow/deny evidence. |
| MUT-FR-007 | 03 | Qualification/training gate | Where configured, confirm required current training, equipment qualification, area qualification or task competency before allowing action. | Expired qualification blocks action. |
| MUT-FR-008 | 03 | State-transition validation | Validate requested command against authoritative current state and allowed transition table; UI state is never authoritative. | Illegal transitions fail deterministically. |
| MUT-FR-009 | 03 | Expected-version concurrency | Require expected aggregate/record version for mutations. Reject stale commands using optimistic concurrency. | Two simultaneous conflicting writes cannot silently overwrite. |
| MUT-FR-010 | 03 | Idempotency | Require idempotency key for commands capable of duplicate submission. Persist key, actor/source, command hash and resulting receipt. | Retries return same result without duplicate regulated event. |
| MUT-FR-011 | 03 | Reason-for-change enforcement | Rules identify commands requiring controlled reason/comment. Reason is structured, required before commit and preserved in audit. | Correction/override cannot proceed without required reason. |
| MUT-FR-012 | 03 | Signature requirement determination | Determine whether electronic signature is required, signature meaning, required signer class and whether one or multiple signatures are required. | Signature need cannot be bypassed by client. |
| MUT-FR-013 | 03 | Signature challenge integration | If signature is required, produce/consume a challenge bound to command, record ID, expected version/hash, meaning and expiry. Commit only after valid signature proof. | Expired/stale challenge prevents commit. |
| MUT-FR-014 | 03 | Domain-rule evaluation | Execute applicable released rule/calculation versions for materials, equipment, limits, eligibility, sequence, QMS and release controls. | Rule result and version are persisted. |
| MUT-FR-015 | 03 | Authoritative PostgreSQL transaction | Persist domain state, new version, audit event and outbox message in one PostgreSQL transaction. | No state can commit without its audit/outbox companion. |
| MUT-FR-016 | 03 | Audit event creation | Create audit record with actor, UTC time, source, action, old/new representation or references, reason, signature, correlation and rule/software versions. | Each committed mutation has auditable event. |
| MUT-FR-017 | 03 | Record hash | Canonicalize resulting regulated record/version and calculate cryptographic digest where the record class requires integrity binding. | Receipt exposes algorithm + digest. |
| MUT-FR-018 | 03 | Transactional outbox | Write integration/domain event into outbox in the same transaction; external bus publishing occurs only after commit. | Bus outage cannot lose committed event. |
| MUT-FR-019 | 03 | Mutation receipt | Return immutable identifiers: command ID, aggregate ID, resulting version, audit event ID, signature ID if applicable, correlation ID and record hash where applicable. | Caller can reconcile exact outcome. |
| MUT-FR-020 | 03 | Projection update isolation | Frappe projection/read model updates occur asynchronously after authoritative commit and may be retried without altering regulatory truth. | Projection failure does not roll back valid GxP commit. |
| MUT-FR-021 | 03 | Failure classification | Return stable machine-readable error codes for authentication, authorization, stale version, state violation, missing signature, rule failure, validation, dependency unavailable and system fault. | Clients do not depend on free-text errors. |
| MUT-FR-022 | 03 | Fail closed for compliance dependencies | If authoritative DB, Signature Service for required signings, Policy Service or integrity-critical component is unavailable, mutation does not succeed. | No degraded-mode bypass. |
| MUT-FR-023 | 03 | Integration identity | ERP/LIMS/Edge commands use non-human identities with narrowly scoped permissions and source-system IDs. | Integration cannot impersonate a human signer. |
| MUT-FR-024 | 03 | Device/input source validation | For machine-originated mutations/evidence, verify registered source/device identity and mapping before acceptance. | Unknown device source rejected/quarantined. |
| MUT-FR-025 | 03 | Late/replayed command control | Detect timestamp/sequence anomalies and duplicate/replayed integration/device commands using source event IDs, sequences and idempotency. | Replay cannot duplicate consumption/result. |
| MUT-FR-026 | 03 | Controlled administrative mutation | Exceptional admin/data-repair actions require dedicated privileged command types, incident/change/deviation reference, stronger authorization and independent review. | No generic DBA correction process. |
| MUT-FR-027 | 03 | Correlation/causation | Every command and generated event carries request, correlation and causation identifiers across services and adapters. | End-to-end trace reconstruction possible. |
| MUT-FR-028 | 03 | Command retention | Retain sufficient command/receipt metadata for investigation, duplicate detection and validation evidence according to record class. | Historic mutation can be reconstructed. |
| MUT-FR-029 | 03 | No arbitrary execution | Command handlers shall call validated domain services; customer-provided Python/JavaScript is prohibited in authoritative mutation execution. | Code injection path absent. |
| MUT-FR-030 | 03 | Schema/version compatibility | Command handlers explicitly support/deprecate schema versions; semantic changes require new version and migration/compatibility assessment. | Existing validated clients do not silently change behavior. |
| MUT-FR-031 | 03 | Security-event interface | Repeated denied, replayed, malformed, privilege-escalation or suspicious mutations generate security monitoring events separate from GxP audit where appropriate. | Security monitoring receives actionable events. |
| MUT-FR-032 | 03 | Inspection/reconciliation support | Provide query by command ID/correlation ID/record to trace command → decision → signature → version → audit → outbox. | QA/validation can prove transaction chain. |
| SIG-FR-001 | 04 | Unique signer identity | Every electronic signature is linked to one immutable individual subject identifier. Display names may change historically, but signer subject cannot be reassigned. | Historical signature remains attributable after rename/deactivation. |
| SIG-FR-002 | 04 | Identity verification responsibility | Customer organization must have a controlled process to verify identity before granting electronic-signature authority; system stores status/evidence reference where configured. | Unverified identity cannot receive signing entitlement. |
| SIG-FR-003 | 04 | Signature meaning catalogue | Controlled meanings include Performed, Verified, Reviewed, Approved, Released, Rejected, Authored, Witnessed and customer-approved extensions. | Meaning is explicit in challenge, record and export. |
| SIG-FR-004 | 04 | Signature policy mapping | Record/action policy defines required meaning, signer role/qualification, number/order of signatures, independent signer restrictions and authentication assurance. | Client cannot alter required signer policy. |
| SIG-FR-005 | 04 | Challenge creation | Create server-side unique signature challenge containing challenge ID, signer subject, tenant/site, record ID, version/hash, action/meaning, nonce and expiry. | Challenge is unique and short-lived. |
| SIG-FR-006 | 04 | Fresh step-up authentication | Every regulated Part 11 signature in V1 requires fresh step-up authentication through configured IdP; normal existing session alone is insufficient. | Recorded authentication time/assurance meets configured policy. |
| SIG-FR-007 | 04 | Identification components | Non-biometric signature configuration must be validated to meet applicable §11.200 component controls. IdP policy must not silently downgrade required factors/components. | Configured test demonstrates required components. |
| SIG-FR-008 | 04 | Continuous-access policy | Although Part 11 distinguishes continuous sessions, V1 intentionally applies fresh step-up for every regulated signature as a stronger product baseline. | No session-only signing path exists. |
| SIG-FR-009 | 04 | Authentication context capture | Persist trusted IdP issuer, subject, authentication time, method/AMR, assurance/ACR where available, session reference and challenge reference. | Signature proves authentication event context. |
| SIG-FR-010 | 04 | Record/version/hash binding | Signature binds exact regulated record ID, version and cryptographic hash (or canonical immutable snapshot ID). | Signature invalid for modified/superseding version. |
| SIG-FR-011 | 04 | Command/action binding | Signature also binds intended action and meaning; an approval signature cannot be reused for release or correction. | Cross-action replay rejected. |
| SIG-FR-012 | 04 | Nonce/replay prevention | Nonce/challenge is single use. Repeated callback/token cannot create second signature. | Replay negative test passes. |
| SIG-FR-013 | 04 | Challenge expiry | Expired challenge cannot be completed; new challenge requires re-evaluation against current record state/version. | Expired challenge fails closed. |
| SIG-FR-014 | 04 | Changed-record invalidation | If record or command-relevant state changes after challenge creation, signature challenge is invalidated. | Stale signing rejected. |
| SIG-FR-015 | 04 | Signature manifestation | Signed record and human-readable export show printed name, execution date/time and signature meaning. | PDF/display test confirms manifestation. |
| SIG-FR-016 | 04 | Signature/record linking | Signature record is linked by immutable identifiers/hash so it cannot be excised, copied or transferred to another record by ordinary application means. | Copying signature ID to another record fails integrity checks. |
| SIG-FR-017 | 04 | Multiple signatures | Support performer/verifier, author/approver, QA reviewer/releaser and other ordered or independent signature chains. | Order and independence enforced server-side. |
| SIG-FR-018 | 04 | Segregation of duties | Policy may require signer != performer/author/previous signer; signer role and qualification checked at signature completion time. | Same-user prohibited scenario rejected. |
| SIG-FR-019 | 04 | Failed attempts | Failed step-up, expired challenge, wrong identity, denied policy and replay attempts do not create valid signature; security-relevant attempts are logged. | No orphan valid signature on failure. |
| SIG-FR-020 | 04 | User deactivation | Disabling signer prevents future signatures but does not invalidate historical legitimate signatures. | Historical exports remain valid. |
| SIG-FR-021 | 04 | Credential reset/recovery | Identity credential recovery is handled by IdP policy; product does not expose old credentials. High-risk recovery may suspend signing until customer process completes. | Recovered account policy testable. |
| SIG-FR-022 | 04 | No signature delegation | Users cannot delegate their electronic signature. Workflow delegation may reassign work but new assignee signs as self. | Delegated task preserves distinct signer. |
| SIG-FR-023 | 04 | Service account prohibition | Service/integration/device identity cannot create human Part 11 signature. | Service token rejected on human signature endpoint. |
| SIG-FR-024 | 04 | Biometric extensibility | Architecture may accept customer IdP biometric/WebAuthn assurance later, but the GxP Signature Service still creates the regulatory signature record. | Authentication technology does not replace GxP record. |
| SIG-FR-025 | 04 | Time source | Signature execution time is assigned server-side in UTC; local timezone is presentation metadata. | Browser clock manipulation has no effect. |
| SIG-FR-026 | 04 | Signer acknowledgement | UI clearly displays what is being signed, meaning, relevant record identity/version and any required statement before step-up. | User cannot sign ambiguous hidden target. |
| SIG-FR-027 | 04 | Signature receipt | Return signature_id, challenge_id, signer subject/name, time, meaning, record/version/hash and auth context reference. | Downstream transaction can reference exact signature. |
| SIG-FR-028 | 04 | Revocation/correction handling | A historical signature is never deleted. If signed record is superseded/corrected, old signature remains on old version; new version requires required new signatures. | Correction preserves prior signatures. |
| SIG-FR-029 | 04 | Customer Part 11 certification support | Provide configurable evidence/report supporting customer's §11.100 certification/governance responsibilities; software does not submit certification automatically unless separately designed. | Responsibility remains explicit. |
| SIG-FR-030 | 04 | Inspection/reporting | Authorized auditor can list all signatures for record/batch/user/time range and export manifestation plus linkage/integrity metadata. | Inspection query is reproducible. |
| AUD-FR-001 | 05 | Independent audit ledger | GxP audit is a dedicated authoritative ledger separate from Frappe Version, application logs, Temporal history and SIEM logs. | Removing Frappe history does not remove GxP audit. |
| AUD-FR-002 | 05 | Automatic generation | Committed regulated mutations automatically generate audit events; users cannot choose whether an applicable event is audited. | No optional audit checkbox. |
| AUD-FR-003 | 05 | UTC timestamp | Each event receives authoritative server UTC time plus source/device timestamp metadata where relevant. | Browser clock irrelevant. |
| AUD-FR-004 | 05 | Actor attribution | Record human/service/device actor type, immutable subject/source ID and display/context metadata. | API/service actions distinguishable from humans. |
| AUD-FR-005 | 05 | Action semantics | Use stable event types: Created, Changed, Corrected, Signed, Approved, Released, StatusChanged, Consumed, Returned, IntegrationAccepted, etc. | Audit is understandable, not generic 'update'. |
| AUD-FR-006 | 05 | Old/new preservation | For changed regulated data preserve old and new values or immutable version references sufficient to reconstruct the change. | Previous information never obscured. |
| AUD-FR-007 | 05 | Changed field set | Record normalized changed fields for review/search without relying only on full JSON diff. | QA can filter changed critical parameters. |
| AUD-FR-008 | 05 | Reason linkage | Store mandatory reason/comment for controlled correction, override, manual replacement, admin repair and other policy-defined changes. | Reason retrievable with event. |
| AUD-FR-009 | 05 | Signature linkage | Audit event references signature ID(s) and meaning where action is signed. | Audit and signature reconcile. |
| AUD-FR-010 | 05 | Record/version linkage | Every event references aggregate/record and resulting version; where applicable record digest. | History order deterministic. |
| AUD-FR-011 | 05 | Correlation/causation | Persist request/correlation/causation IDs to connect UI command, background activity and integration side effects. | Investigation trace end-to-end. |
| AUD-FR-012 | 05 | Source attribution | Identify Frappe UI, REST API, ERP, LIMS, Edge, background system, migration or privileged repair source. | Source reports possible. |
| AUD-FR-013 | 05 | Software/rule version | Record product release and critical rule/calculation version used for action where relevant. | Historical decision reproducible. |
| AUD-FR-014 | 05 | Append-only application permissions | Application DB role may INSERT audit events and SELECT authorized records; no UPDATE/DELETE privilege for audit tables. | Privilege test enforced. |
| AUD-FR-015 | 05 | Partitioning without semantic loss | Time/tenant partitioning permitted for scale, but event IDs/order, retention and search remain consistent. | Partition maintenance cannot erase retained events. |
| AUD-FR-016 | 05 | Per-record hash chain | Regulated aggregate event streams include previous event hash/current event hash using canonical event representation. | Tampering detectable. |
| AUD-FR-017 | 05 | Integrity checkpoints | Periodically create signed integrity manifest/Merkle-style root or equivalent over audit ranges and store in immutable-capable storage. | Independent verification possible. |
| AUD-FR-018 | 05 | Integrity verification job | Scheduled process verifies chain/checkpoint consistency and alarms on mismatch/missing ranges. | Tamper issue not silent. |
| AUD-FR-019 | 05 | Privileged DB monitoring | DBA/cloud-admin access and extraordinary actions are monitored through independent infrastructure/security logs and controlled procedures. | DBA is not invisible. |
| AUD-FR-020 | 05 | Audit review UI | Authorized QA/auditor can filter by record, batch, user, event type, field, time, site, signature, source and reason. | Review does not require SQL. |
| AUD-FR-021 | 05 | Audit review annotations | If customer procedure requires documented audit-trail review, create separate review record/signature without changing the underlying audit events. | Audit event remains immutable. |
| AUD-FR-022 | 05 | Export | Generate human-readable and structured audit export tied to exact record/export manifest and integrity checks. | Inspection-ready. |
| AUD-FR-023 | 05 | Retention | Audit retained at least as long as associated regulated record policy; archival retains search/retrieval and integrity evidence. | No premature purge. |
| AUD-FR-024 | 05 | Legal/quality hold | Retention engine can suspend disposal/archive transitions for held records/events. | Held audit preserved. |
| AUD-FR-025 | 05 | Sensitive-data handling | Operational logs may redact sensitive values, but authorized GxP audit/evidence must preserve required content/meaning. Secrets must never be captured. | No credential leakage. |
| AUD-FR-026 | 05 | Migration audit | Migrated records include provenance/migration events and source checksums without pretending migrated events occurred natively. | Migration distinguishable. |
| AUD-FR-027 | 05 | Failed-action security trail | Policy-denied/replay/attack events may be sent to security ledger/SIEM; only failed actions with GxP significance need GxP audit according to risk/policy. | Avoid misleading committed-record audit. |
| AUD-FR-028 | 05 | Time ordering | Persist per-aggregate monotonic version/sequence and database commit order metadata where needed; source timestamp does not control authoritative order. | Late device data handled explicitly. |
| AUD-FR-029 | 05 | Backup/restore integrity | Restore procedure verifies audit record counts, hash checkpoints, references and signature linkage. | Restore qualification includes integrity. |
| AUD-FR-030 | 05 | No ordinary purge UI | Application users and admins cannot delete audit events via normal UI/API. Retention disposal, if ever permitted, is a separately controlled archival process based on applicable policy. | Deletion path controlled and testable. |
| VLT-FR-001 | 06 | Immutable released version | Every released master, specification, controlled document snapshot and regulated final record receives immutable vault version ID. | Released content cannot be edited in place. |
| VLT-FR-002 | 06 | Canonical snapshot | Vault stores canonical structured representation sufficient to reproduce content/meaning independent of mutable Frappe master. | Changing Frappe draft does not change vault object. |
| VLT-FR-003 | 06 | Cryptographic digest | Calculate and store algorithm + digest over canonical representation and evidence manifest. | Integrity test reproducible. |
| VLT-FR-004 | 06 | Release metadata | Store object type, business ID, version, status, effective dates, release reason, authors/approvers/signatures and software/schema versions. | Full release context retained. |
| VLT-FR-005 | 06 | Evidence manifest | Link immutable file/evidence IDs, hashes, media types and versions used by released object. | Attachments cannot silently swap. |
| VLT-FR-006 | 06 | Batch issue snapshot | At batch/device work issuance, freeze exact released recipe/specification/material/equipment/rule references required for that execution. | Later master change cannot rewrite active/history. |
| VLT-FR-007 | 06 | Snapshot dependency closure | Snapshot captures exact IDs/versions/hashes of dependent released objects rather than only business names. | Dependency reproducible. |
| VLT-FR-008 | 06 | Effective dating | Released versions have controlled effective-from/effective-to/obsolete lifecycle; selection engine prevents unauthorized obsolete/future use. | Batch issue chooses eligible version. |
| VLT-FR-009 | 06 | Supersession | New approved version supersedes prior for future use but never deletes prior version or its historical references. | Old batches still resolve old version. |
| VLT-FR-010 | 06 | Controlled correction | Corrections to regulated completed/released records create amendment/superseding version referencing original, reason, authority, signatures and changed fields. | Original remains visible. |
| VLT-FR-011 | 06 | Correction eligibility | Policy defines which record states/types permit correction, who may initiate/approve, and whether downstream impact assessment is required. | Unauthorized correction blocked. |
| VLT-FR-012 | 06 | No silent overwrite | Any attempt to overwrite a vault object/version through application API is rejected. | Immutability negative test. |
| VLT-FR-013 | 06 | Void/cancel semantics | Where a record must be voided/cancelled, retain original and add controlled status/event/reason rather than physical deletion. | Voided history remains. |
| VLT-FR-014 | 06 | Signature binding | Signatures reference exact vault version/hash or pre-commit canonical target that becomes exact resulting version. | Signature cannot float to new content. |
| VLT-FR-015 | 06 | Audit linkage | Version creation/release/supersession/correction is represented in Audit Ledger. | Vault history and audit reconcile. |
| VLT-FR-016 | 06 | Inspection retrieval | Authorized user can retrieve any historical version plus relationships, signatures, audit and evidence manifest. | Historical record is readable. |
| VLT-FR-017 | 06 | Deterministic export | Export service can regenerate human-readable representation from stored authoritative version using controlled renderer/version or preserve signed release export. | Meaning remains available after upgrade. |
| VLT-FR-018 | 06 | Schema evolution | Older canonical schema versions remain readable. Migrations never rewrite historical semantic content without controlled migration provenance. | Old records survive software upgrade. |
| VLT-FR-019 | 06 | Retention class | Each object gets retention class based on profile/record type/customer policy; no normal application deletion. | Retention auditable. |
| VLT-FR-020 | 06 | Legal/quality hold | Hold prevents disposal/archival transitions and is itself controlled/audited. | Hold honored. |
| VLT-FR-021 | 06 | Archive tiering | Move old vault objects/evidence to archival storage only if integrity, retrieval and meaning are preserved. | Archive retrieval qualified. |
| VLT-FR-022 | 06 | WORM-capable evidence | Released file packages/checkpoints may use object-storage retention lock/WORM where deployment supports it. | Infrastructure immutability can be verified. |
| VLT-FR-023 | 06 | Version numbering | Use immutable internal version IDs plus human/business version labels; never rely only on editable semantic label. | Duplicate labels cannot confuse history. |
| VLT-FR-024 | 06 | Content addressing | Evidence objects may be deduplicated by digest while preserving record-specific manifest references and retention. | No cross-record mutation. |
| VLT-FR-025 | 06 | Cross-constituent snapshot | DDCP snapshot can bind exact drug constituent version, device constituent version, compatibility version and final assembly/release rules. | Final DDCP scope reproducible. |
| VLT-FR-026 | 06 | Migration provenance | Imported historical versions are flagged migrated, with source system, source ID, extraction checksum and migration batch. | Native vs migrated distinguishable. |
| VLT-FR-027 | 06 | Restore verification | Backup restore checks version counts, hashes, evidence manifests, signatures and audit relationships. | Restored vault trustworthy. |
| VLT-FR-028 | 06 | Access control | Draft authorship access does not imply released-vault write access; runtime exposes read plus controlled release/correction commands only. | Least privilege. |
| VLT-FR-029 | 06 | Reference integrity | Foreign references to released version use immutable identifiers and DB constraints/service validation; no dangling reference on normal operation. | Batch can always resolve snapshot. |
| VLT-FR-030 | 06 | Disposition package | Final release/closure creates or references a complete immutable record package suitable for regulatory export and long-term retrieval. | Release package complete. |
| IAM-FR-001 | 07 | Unique human identity | Each user has immutable internal subject mapping to enterprise identity; shared regulated accounts prohibited. | Two users cannot share signing identity. |
| IAM-FR-002 | 07 | External identity federation | Support OIDC/SAML through Keycloak-compatible boundary; customer Entra/Okta/AD or equivalent may be source. | Authentication provider replaceable. |
| IAM-FR-003 | 07 | Local identity fallback | On-prem deployments may use controlled local Keycloak identity where customer SSO unavailable, subject to equivalent policies. | No cloud IdP hard dependency. |
| IAM-FR-004 | 07 | User lifecycle | Provision, activate, suspend, disable, terminate and retain historical identity metadata. | Disabled user cannot act/sign. |
| IAM-FR-005 | 07 | Role catalogue | Reference roles grouped by Production, QA, QC, Warehouse, Procurement, Engineering, QMS, IT and Auditor. | Role names configurable but permissions controlled. |
| IAM-FR-006 | 07 | Permission actions | Permissions are action/resource based, not merely screen access: view, create-draft, execute, verify, approve, release, correct, administer, export, etc. | UI hiding not permission. |
| IAM-FR-007 | 07 | Tenant scope | Identity cannot access another customer environment/data. | Isolation negative test. |
| IAM-FR-008 | 07 | Site/area scope | User access can be limited to site, building, area/room/line and function where required. | Cross-site operation blocked. |
| IAM-FR-009 | 07 | Product/process scope | Authorization may restrict user to product family, process type or specialized operation. | Specialized task protected. |
| IAM-FR-010 | 07 | Qualification object | Model qualifications such as dispensing, sterile-area, aseptic operation, QA release, equipment use and specialized testing. | Qualification has status/effective/expiry. |
| IAM-FR-011 | 07 | Training gate | Required training/SOP curriculum status can be evaluated before execution/signing. | Expired training blocks configured action. |
| IAM-FR-012 | 07 | Equipment qualification authorization | User may require equipment-specific or class qualification before operating/verifying. | Execution gate server-side. |
| IAM-FR-013 | 07 | Signature entitlement | Only users with active electronic-signature entitlement and verified identity status may complete regulated signature challenges. | Role alone insufficient. |
| IAM-FR-014 | 07 | Segregation-of-duties policy | Support performer != verifier, author != approver, independent QA release, and configurable incompatible role/action combinations. | Same-user negative tests. |
| IAM-FR-015 | 07 | Dynamic SoD context | SoD evaluates record history, not only static role membership; e.g. user who performed step cannot verify same step. | History-aware decision. |
| IAM-FR-016 | 07 | Delegation of work | Tasks/approvals may be reassigned/delegated under controlled workflow, but electronic signature is never delegated. | New assignee signs self. |
| IAM-FR-017 | 07 | Temporary authorization | Time-limited authorization has reason, scope, start/end, approver and audit; auto-expires. | No permanent hidden elevation. |
| IAM-FR-018 | 07 | Break-glass access | Emergency access is explicitly invoked, MFA-protected, time-limited, reason-coded, heavily audited and independently reviewed. | Emergency use visible. |
| IAM-FR-019 | 07 | Privileged role separation | Application admin, Security admin, Identity admin, DB admin and infrastructure admin remain separate from product release authority. | Admin cannot release by privilege. |
| IAM-FR-020 | 07 | Vendor support access | Support access requires customer-approved/time-limited identity, scoped permissions and logging; no shared vendor root account. | Support access traceable. |
| IAM-FR-021 | 07 | Service accounts | Non-human identities have owner, purpose, scopes, credential/certificate lifecycle, rotation and no human signature capability. | Service identity inventory complete. |
| IAM-FR-022 | 07 | Device identities | Edge/instruments use registered non-human device identities/certificates separate from service/human users. | Machine evidence attributable. |
| IAM-FR-023 | 07 | Session controls | Configurable idle/absolute timeout, reauthentication rules and session revocation. Regulated signature still uses fresh step-up. | Stolen long session limited. |
| IAM-FR-024 | 07 | MFA | MFA required for privileged access and configured enterprise policies; signature authentication follows Document 04 assurance. | Privileged account cannot use password-only baseline. |
| IAM-FR-025 | 07 | Role assignment approval | High-risk role/entitlement assignment uses controlled approval and audit; assignment effective dates supported. | QA release role cannot self-assign. |
| IAM-FR-026 | 07 | Access review | Periodic report/review of active users, roles, sites, qualifications, service accounts and privileged access. | Review evidence exportable. |
| IAM-FR-027 | 07 | Joiner/mover/leaver | Identity changes synchronize through IdP/manual process while preserving immutable historical actor IDs. | Department change doesn't rewrite history. |
| IAM-FR-028 | 07 | Policy decision evidence | Authorization response contains allow/deny, policy version, evaluated subject/resource/action and reason codes. | Validation can prove why denied. |
| IAM-FR-029 | 07 | Least privilege defaults | New users/service accounts have no regulated privileges until explicitly assigned. | Default deny. |
| IAM-FR-030 | 07 | No client-side authority | Frappe permissions improve UX but GxP Policy Service independently enforces every authoritative regulated action. | API bypass fails. |
| IAM-FR-031 | 07 | Qualification override | Any permitted emergency qualification override requires dedicated policy, reason, authorized signer and quality-event/audit linkage. | No silent override. |
| IAM-FR-032 | 07 | Historical access | User/account deletion is avoided where history is required; deactivated identity remains referencable for old records/signatures. | Old actor resolves. |
| RUL-FR-001 | 08 | Controlled rule object | Every GxP-critical rule/formula has stable ID, type, semantic version, status, scope and owner. | Rule identifiable in historical decision. |
| RUL-FR-002 | 08 | Rule lifecycle | Draft → Review → Approved/Released → Effective → Superseded/Retired. Released version immutable. | No in-place formula edit. |
| RUL-FR-003 | 08 | Effective dating | Rule version has effective-from/to and profile/site/product applicability; execution snapshots exact eligible version. | Future/obsolete rule not selected. |
| RUL-FR-004 | 08 | Deterministic evaluation | Same inputs + same released rule version produce same result, independent of UI/server instance. | Golden tests deterministic. |
| RUL-FR-005 | 08 | Safe expression language | GxP formulas/rules use constrained DSL/AST/function catalogue; arbitrary Python/JavaScript/SQL/network/file execution prohibited. | Expression cannot execute arbitrary code. |
| RUL-FR-006 | 08 | Typed inputs | Inputs define data type, unit, required/optional, precision, acceptable null behavior and source. | Wrong unit/type rejected. |
| RUL-FR-007 | 08 | Typed outputs | Outputs define result type, unit, precision, status/reason codes and downstream action. | Consumers contract stable. |
| RUL-FR-008 | 08 | Unit management | Use canonical UOM IDs and validated conversions; dimensional incompatibility rejected. | kg cannot be silently compared to L. |
| RUL-FR-009 | 08 | Decimal arithmetic | Use deterministic decimal arithmetic for regulated calculations; avoid binary floating-point where it could alter results. | Precision tests pass. |
| RUL-FR-010 | 08 | Rounding rules | Formula defines rounding mode, stage and decimal places/significant figures. | Rounding is explicit/versioned. |
| RUL-FR-011 | 08 | Limit rules | Support inclusive/exclusive min/max, target/tolerance, enumerations, ranges and conditional limits. | Boundary tests included. |
| RUL-FR-012 | 08 | Eligibility rules | Material, equipment, operator, area, recipe and constituent eligibility rules evaluate before relevant action. | Ineligible resource blocks. |
| RUL-FR-013 | 08 | Sequence/progression rules | Define prerequisite steps, parallel joins, conditional branches, hold points and permitted progression. | Out-of-sequence command denied. |
| RUL-FR-014 | 08 | Signature rules | Determine required signature meaning, signer role/qualification, independence and count/order. | Signature policy version captured. |
| RUL-FR-015 | 08 | Deviation/exception triggers | Out-of-limit, expired status, manual override, timing breach, environment excursion or missing evidence can generate configured exception/hold. | Trigger result deterministic. |
| RUL-FR-016 | 08 | Release rules | Aggregate required completion/QC/QMS/reconciliation/signature/equipment/environment evidence into release eligibility result with blockers. | Release reason codes explainable. |
| RUL-FR-017 | 08 | Yield calculation | Support theoretical/actual/stage yield and percentage according to released formula, input sources, verification policy and rounding. | §211.103-type scenarios testable where applicable. |
| RUL-FR-018 | 08 | Potency/assay adjustment | Support controlled potency correction with exact assay source/version, formula, units and precision. | Material quantity traceable. |
| RUL-FR-019 | 08 | Reconciliation calculation | Issued/dispensed/consumed/returned/rejected/destroyed quantities reconcile according to released rule/tolerance. | Variance creates blocker/event. |
| RUL-FR-020 | 08 | Time-window rules | Support process hold times, expiry/retest, calibration due, training expiry, timer limits and environmental windows using authoritative time. | Boundary/timezone tests pass. |
| RUL-FR-021 | 08 | Decision explanation | Every evaluation returns rule ID/version, inputs/reference IDs, outcome, reason codes and relevant calculated values. | QA can explain decision. |
| RUL-FR-022 | 08 | Evaluation persistence | Persist critical evaluation result/reference with regulated mutation/audit; avoid relying on recomputation under a newer rule. | Historical result reproducible. |
| RUL-FR-023 | 08 | Simulation/test mode | Authorized users can simulate draft rules against test/historical sanitized data without affecting regulated state. | Simulation clearly non-production. |
| RUL-FR-024 | 08 | Rule test cases | Each released critical rule includes approved positive, boundary, negative and error test vectors. | No release without tests. |
| RUL-FR-025 | 08 | Independent verification | Critical formulas can require independent reviewer approval/test evidence before release. | Formula author cannot self-approve if policy says no. |
| RUL-FR-026 | 08 | Change impact | Changing rule/formula triggers impact assessment for products, recipes, batches, tests, validation and customer configuration. | Affected scope report generated. |
| RUL-FR-027 | 08 | Snapshot binding | Batch/record snapshots reference exact rule/calculation versions required for execution. | Mid-batch rule change does not alter history. |
| RUL-FR-028 | 08 | External result rules | LIMS/ERP/Edge values are validated against source mapping, unit, schema and quality before rule evaluation. | Bad source data fails/quarantines. |
| RUL-FR-029 | 08 | Missing/invalid inputs | Rule defines explicit behavior: fail, hold, not-applicable or exception; never silently substitute default for critical missing data unless released rule permits. | Missing critical input cannot pass. |
| RUL-FR-030 | 08 | Overflow/domain errors | Divide-by-zero, invalid logarithm/range, overflow, unit mismatch or invalid enum produce controlled failure with no fabricated result. | Calculation errors observable. |
| RUL-FR-031 | 08 | Rule engine versioning | Record engine/runtime version separately from business rule version; engine upgrade requires regression. | Same rule under new engine validated. |
| RUL-FR-032 | 08 | Performance/cache safety | Caching compiled rules is allowed only if cache key includes immutable rule version and tenant/profile; cache cannot alter deterministic outcome. | No stale rule execution. |
