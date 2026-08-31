# Part 11 electronic signature

**Purpose:** Part 11 electronic signature for the eBMR/eDHR platform.
**Applicable paths/modules:** see `docs/generated/17_REPOSITORY_STRUCTURE.md`; this rule applies to every
service, the Frappe app, edge and integration code unless a narrower scope is stated below.
**Source documents:** Document 04 (SPEC-GXP-002), Document 88 (SPEC-VAL-010), Document 07 (SPEC-IAM-001)
**Source requirement IDs:** SIG-FR-001..030 (30); P11-FR-001..026 (26); IAM-FR-001..032 (32)

---

## Required implementation pattern

Resolve the requirement from **policy data** (Document 106 `sig_policy`), never from code conditionals.
Create one challenge per required signature, bound to record id + version + hash + action + meaning, with
a single-use nonce and expiry. Require fresh step-up authentication for every regulated signature.
Re-evaluate independence and qualification at completion time. Commit only after all proofs are valid.

## Forbidden patterns

- session/MFA treated as a signature
- signature meaning as free text
- service, integration or device identity signing
- signature reuse across actions or versions
- deleting or transferring a historical signature
- client-supplied "signed" flags

## Required tests

expired challenge; replayed nonce; record changed after challenge; wrong signer class; performer signing
as verifier; out-of-order chain; service token on the signature endpoint; deactivated signer; manifestation
in UI and PDF; policy version binding on a historic record.


## Source requirements (extract)

| ID | Requirement | Required behaviour |
|---|---|---|
| SIG-FR-001 | Unique signer identity | Every electronic signature is linked to one immutable individual subject identifier. Display names may change historically, but signer subject cannot be reassigned. |
| SIG-FR-002 | Identity verification responsibility | Customer organization must have a controlled process to verify identity before granting electronic-signature authority; system stores status/evidence reference where configured. |
| SIG-FR-003 | Signature meaning catalogue | Controlled meanings include Performed, Verified, Reviewed, Approved, Released, Rejected, Authored, Witnessed and customer-approved extensions. |
| SIG-FR-004 | Signature policy mapping | Record/action policy defines required meaning, signer role/qualification, number/order of signatures, independent signer restrictions and authentication assurance. |
| SIG-FR-005 | Challenge creation | Create server-side unique signature challenge containing challenge ID, signer subject, tenant/site, record ID, version/hash, action/meaning, nonce and expiry. |
| SIG-FR-006 | Fresh step-up authentication | Every regulated Part 11 signature in V1 requires fresh step-up authentication through configured IdP; normal existing session alone is insufficient. |
| SIG-FR-007 | Identification components | Non-biometric signature configuration must be validated to meet applicable §11.200 component controls. IdP policy must not silently downgrade required factors/components. |
| SIG-FR-008 | Continuous-access policy | Although Part 11 distinguishes continuous sessions, V1 intentionally applies fresh step-up for every regulated signature as a stronger product baseline. |
| SIG-FR-009 | Authentication context capture | Persist trusted IdP issuer, subject, authentication time, method/AMR, assurance/ACR where available, session reference and challenge reference. |
| SIG-FR-010 | Record/version/hash binding | Signature binds exact regulated record ID, version and cryptographic hash (or canonical immutable snapshot ID). |
| SIG-FR-011 | Command/action binding | Signature also binds intended action and meaning; an approval signature cannot be reused for release or correction. |
| SIG-FR-012 | Nonce/replay prevention | Nonce/challenge is single use. Repeated callback/token cannot create second signature. |
| SIG-FR-013 | Challenge expiry | Expired challenge cannot be completed; new challenge requires re-evaluation against current record state/version. |
| SIG-FR-014 | Changed-record invalidation | If record or command-relevant state changes after challenge creation, signature challenge is invalidated. |
| SIG-FR-015 | Signature manifestation | Signed record and human-readable export show printed name, execution date/time and signature meaning. |
| SIG-FR-016 | Signature/record linking | Signature record is linked by immutable identifiers/hash so it cannot be excised, copied or transferred to another record by ordinary application means. |
| SIG-FR-017 | Multiple signatures | Support performer/verifier, author/approver, QA reviewer/releaser and other ordered or independent signature chains. |
| SIG-FR-018 | Segregation of duties | Policy may require signer != performer/author/previous signer; signer role and qualification checked at signature completion time. |
| SIG-FR-019 | Failed attempts | Failed step-up, expired challenge, wrong identity, denied policy and replay attempts do not create valid signature; security-relevant attempts are logged. |
| SIG-FR-020 | User deactivation | Disabling signer prevents future signatures but does not invalidate historical legitimate signatures. |
| SIG-FR-021 | Credential reset/recovery | Identity credential recovery is handled by IdP policy; product does not expose old credentials. High-risk recovery may suspend signing until customer process completes. |
| SIG-FR-022 | No signature delegation | Users cannot delegate their electronic signature. Workflow delegation may reassign work but new assignee signs as self. |
| SIG-FR-023 | Service account prohibition | Service/integration/device identity cannot create human Part 11 signature. |
| SIG-FR-024 | Biometric extensibility | Architecture may accept customer IdP biometric/WebAuthn assurance later, but the GxP Signature Service still creates the regulatory signature record. |
| SIG-FR-025 | Time source | Signature execution time is assigned server-side in UTC; local timezone is presentation metadata. |
| SIG-FR-026 | Signer acknowledgement | UI clearly displays what is being signed, meaning, relevant record identity/version and any required statement before step-up. |
| SIG-FR-027 | Signature receipt | Return signature_id, challenge_id, signer subject/name, time, meaning, record/version/hash and auth context reference. |
| SIG-FR-028 | Revocation/correction handling | A historical signature is never deleted. If signed record is superseded/corrected, old signature remains on old version; new version requires required new signatures. |
| SIG-FR-029 | Customer Part 11 certification support | Provide configurable evidence/report supporting customer's §11.100 certification/governance responsibilities; software does not submit certification automatically unless separately designed. |
| SIG-FR-030 | Inspection/reporting | Authorized auditor can list all signatures for record/batch/user/time range and export manifestation plus linkage/integrity metadata. |
| P11-FR-001 | Part 11 scope | Identify records/signatures relied upon electronically under predicate rules. |
| P11-FR-002 | Accuracy/reliability | Verify intended functions create accurate/reliable records. |
| P11-FR-003 | Altered record discernment | Verify invalid/altered record detection. |
| P11-FR-004 | Human-readable copies | Verify accurate complete human-readable export. |
| P11-FR-005 | Electronic copies | Verify electronic export with required metadata. |
| P11-FR-006 | Retention/retrieval | Verify ready retrieval through retention/archive. |
| P11-FR-007 | Access | Verify authorized-only record/system access. |
| P11-FR-008 | Audit trail | Verify secure timestamped audit, prior values, retention/review. |
| P11-FR-009 | Operational checks | Verify sequencing prevents invalid workflow order. |
| P11-FR-010 | Authority checks | Verify role/qualification/SoD/signature authority. |

## SPEC_GAP triggers

Raise a SPEC_GAP rather than deciding, if you encounter: a missing signature/authorization/retention/
precision value, a conflict between two source documents, an entity without an owner, an event without a
producer, or any requirement that would need a regulated behaviour you cannot trace to
Document 04, Document 88, Document 07 or Documents 106–115.
