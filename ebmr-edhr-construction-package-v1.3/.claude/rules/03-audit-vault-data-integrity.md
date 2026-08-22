# Audit ledger, Vault and data integrity

**Purpose:** Audit ledger, Vault and data integrity for the eBMR/eDHR platform.
**Applicable paths/modules:** see `docs/generated/17_REPOSITORY_STRUCTURE.md`; this rule applies to every
service, the Frappe app, edge and integration code unless a narrower scope is stated below.
**Source documents:** Document 05 (SPEC-GXP-003), Document 06 (SPEC-GXP-004), Document 89 (SPEC-VAL-011), Document 72 (SPEC-DATA-004)
**Source requirement IDs:** AUD-FR-001..030 (30); VLT-FR-001..030 (30); DIV-FR-001..024 (24); OBJ-FR-001..030 (30)

---

## Required implementation pattern

Audit rows are append-only and written in the same transaction as the state change. Released versions go
to the Vault with canonical form, digest and evidence manifest. Corrections supersede; they never edit.
Per-record-stream hash chaining plus periodic signed checkpoints provide tamper evidence.

## Forbidden patterns

- `UPDATE` / `DELETE` on audit, signature, vault or evidence tables (enforced at database privilege level)
- editing a failed test, OOS result or released record into a "clean" state
- writing evidence without a digest and manifest entry
- retention shortening or purge without an approved disposal decision (Document 108)

## Required tests

failure injection proving state cannot commit without audit; privilege-level UPDATE/DELETE rejection;
hash-chain verification; checkpoint replay detection; correction preserves original; retention inheritance;
restore does not resurrect disposed records.


## Source requirements (extract)

| ID | Requirement | Required behaviour |
|---|---|---|
| AUD-FR-001 | Independent audit ledger | GxP audit is a dedicated authoritative ledger separate from Frappe Version, application logs, Temporal history and SIEM logs. |
| AUD-FR-002 | Automatic generation | Committed regulated mutations automatically generate audit events; users cannot choose whether an applicable event is audited. |
| AUD-FR-003 | UTC timestamp | Each event receives authoritative server UTC time plus source/device timestamp metadata where relevant. |
| AUD-FR-004 | Actor attribution | Record human/service/device actor type, immutable subject/source ID and display/context metadata. |
| AUD-FR-005 | Action semantics | Use stable event types: Created, Changed, Corrected, Signed, Approved, Released, StatusChanged, Consumed, Returned, IntegrationAccepted, etc. |
| AUD-FR-006 | Old/new preservation | For changed regulated data preserve old and new values or immutable version references sufficient to reconstruct the change. |
| AUD-FR-007 | Changed field set | Record normalized changed fields for review/search without relying only on full JSON diff. |
| AUD-FR-008 | Reason linkage | Store mandatory reason/comment for controlled correction, override, manual replacement, admin repair and other policy-defined changes. |
| AUD-FR-009 | Signature linkage | Audit event references signature ID(s) and meaning where action is signed. |
| AUD-FR-010 | Record/version linkage | Every event references aggregate/record and resulting version; where applicable record digest. |
| AUD-FR-011 | Correlation/causation | Persist request/correlation/causation IDs to connect UI command, background activity and integration side effects. |
| AUD-FR-012 | Source attribution | Identify Frappe UI, REST API, ERP, LIMS, Edge, background system, migration or privileged repair source. |
| AUD-FR-013 | Software/rule version | Record product release and critical rule/calculation version used for action where relevant. |
| AUD-FR-014 | Append-only application permissions | Application DB role may INSERT audit events and SELECT authorized records; no UPDATE/DELETE privilege for audit tables. |
| AUD-FR-015 | Partitioning without semantic loss | Time/tenant partitioning permitted for scale, but event IDs/order, retention and search remain consistent. |
| AUD-FR-016 | Per-record hash chain | Regulated aggregate event streams include previous event hash/current event hash using canonical event representation. |
| AUD-FR-017 | Integrity checkpoints | Periodically create signed integrity manifest/Merkle-style root or equivalent over audit ranges and store in immutable-capable storage. |
| AUD-FR-018 | Integrity verification job | Scheduled process verifies chain/checkpoint consistency and alarms on mismatch/missing ranges. |
| AUD-FR-019 | Privileged DB monitoring | DBA/cloud-admin access and extraordinary actions are monitored through independent infrastructure/security logs and controlled procedures. |
| AUD-FR-020 | Audit review UI | Authorized QA/auditor can filter by record, batch, user, event type, field, time, site, signature, source and reason. |
| AUD-FR-021 | Audit review annotations | If customer procedure requires documented audit-trail review, create separate review record/signature without changing the underlying audit events. |
| AUD-FR-022 | Export | Generate human-readable and structured audit export tied to exact record/export manifest and integrity checks. |
| AUD-FR-023 | Retention | Audit retained at least as long as associated regulated record policy; archival retains search/retrieval and integrity evidence. |
| AUD-FR-024 | Legal/quality hold | Retention engine can suspend disposal/archive transitions for held records/events. |
| AUD-FR-025 | Sensitive-data handling | Operational logs may redact sensitive values, but authorized GxP audit/evidence must preserve required content/meaning. Secrets must never be captured. |
| AUD-FR-026 | Migration audit | Migrated records include provenance/migration events and source checksums without pretending migrated events occurred natively. |
| AUD-FR-027 | Failed-action security trail | Policy-denied/replay/attack events may be sent to security ledger/SIEM; only failed actions with GxP significance need GxP audit according to risk/policy. |
| AUD-FR-028 | Time ordering | Persist per-aggregate monotonic version/sequence and database commit order metadata where needed; source timestamp does not control authoritative order. |
| AUD-FR-029 | Backup/restore integrity | Restore procedure verifies audit record counts, hash checkpoints, references and signature linkage. |
| AUD-FR-030 | No ordinary purge UI | Application users and admins cannot delete audit events via normal UI/API. Retention disposal, if ever permitted, is a separately controlled archival process based on applicable policy. |
| VLT-FR-001 | Immutable released version | Every released master, specification, controlled document snapshot and regulated final record receives immutable vault version ID. |
| VLT-FR-002 | Canonical snapshot | Vault stores canonical structured representation sufficient to reproduce content/meaning independent of mutable Frappe master. |
| VLT-FR-003 | Cryptographic digest | Calculate and store algorithm + digest over canonical representation and evidence manifest. |
| VLT-FR-004 | Release metadata | Store object type, business ID, version, status, effective dates, release reason, authors/approvers/signatures and software/schema versions. |
| VLT-FR-005 | Evidence manifest | Link immutable file/evidence IDs, hashes, media types and versions used by released object. |
| VLT-FR-006 | Batch issue snapshot | At batch/device work issuance, freeze exact released recipe/specification/material/equipment/rule references required for that execution. |
| VLT-FR-007 | Snapshot dependency closure | Snapshot captures exact IDs/versions/hashes of dependent released objects rather than only business names. |
| VLT-FR-008 | Effective dating | Released versions have controlled effective-from/effective-to/obsolete lifecycle; selection engine prevents unauthorized obsolete/future use. |
| VLT-FR-009 | Supersession | New approved version supersedes prior for future use but never deletes prior version or its historical references. |
| VLT-FR-010 | Controlled correction | Corrections to regulated completed/released records create amendment/superseding version referencing original, reason, authority, signatures and changed fields. |

## SPEC_GAP triggers

Raise a SPEC_GAP rather than deciding, if you encounter: a missing signature/authorization/retention/
precision value, a conflict between two source documents, an entity without an owner, an event without a
producer, or any requirement that would need a regulated behaviour you cannot trace to
Document 05, Document 06, Document 89, Document 72 or Documents 106–115.
