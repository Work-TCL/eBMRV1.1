# WP-01 — Traceability Matrix

**Scope:** The regulated kernel: every later module depends on these six services.  
**Requirements:** 186  |  **Test cases:** 537

| Requirement | Module | Risk | Signature | Test cases | Build stage | Verified | Validated |
|---|---|---|---|---|---|---|---|
| MUT-FR-001 — Single regulated mutation entry point | SPEC-GXP-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-002 — Authenticated actor context | SPEC-GXP-001 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-003 — Tenant/site scope enforcement | SPEC-GXP-001 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-004 — Command classification | SPEC-GXP-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-005 — Schema validation | SPEC-GXP-001 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-006 — Authorization decision | SPEC-GXP-001 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-007 — Qualification/training gate | SPEC-GXP-001 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-008 — State-transition validation | SPEC-GXP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-009 — Expected-version concurrency | SPEC-GXP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-010 — Idempotency | SPEC-GXP-001 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-011 — Reason-for-change enforcement | SPEC-GXP-001 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-012 — Signature requirement determination | SPEC-GXP-001 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-013 — Signature challenge integration | SPEC-GXP-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-014 — Domain-rule evaluation | SPEC-GXP-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-015 — Authoritative PostgreSQL transaction | SPEC-GXP-001 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-016 — Audit event creation | SPEC-GXP-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-017 — Record hash | SPEC-GXP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-018 — Transactional outbox | SPEC-GXP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-019 — Mutation receipt | SPEC-GXP-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-020 — Projection update isolation | SPEC-GXP-001 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-021 — Failure classification | SPEC-GXP-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-022 — Fail closed for compliance dependencies | SPEC-GXP-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-023 — Integration identity | SPEC-GXP-001 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-024 — Device/input source validation | SPEC-GXP-001 | H | yes | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-025 — Late/replayed command control | SPEC-GXP-001 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-026 — Controlled administrative mutation | SPEC-GXP-001 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-027 — Correlation/causation | SPEC-GXP-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-028 — Command retention | SPEC-GXP-001 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-029 — No arbitrary execution | SPEC-GXP-001 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-030 — Schema/version compatibility | SPEC-GXP-001 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-031 — Security-event interface | SPEC-GXP-001 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| MUT-FR-032 — Inspection/reconciliation support | SPEC-GXP-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-001 — Unique signer identity | SPEC-GXP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-002 — Identity verification responsibility | SPEC-GXP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-003 — Signature meaning catalogue | SPEC-GXP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-004 — Signature policy mapping | SPEC-GXP-002 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-005 — Challenge creation | SPEC-GXP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-006 — Fresh step-up authentication | SPEC-GXP-002 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-007 — Identification components | SPEC-GXP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-008 — Continuous-access policy | SPEC-GXP-002 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-009 — Authentication context capture | SPEC-GXP-002 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-010 — Record/version/hash binding | SPEC-GXP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-011 — Command/action binding | SPEC-GXP-002 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-012 — Nonce/replay prevention | SPEC-GXP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-013 — Challenge expiry | SPEC-GXP-002 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-014 — Changed-record invalidation | SPEC-GXP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-015 — Signature manifestation | SPEC-GXP-002 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-016 — Signature/record linking | SPEC-GXP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-017 — Multiple signatures | SPEC-GXP-002 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-018 — Segregation of duties | SPEC-GXP-002 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-019 — Failed attempts | SPEC-GXP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-020 — User deactivation | SPEC-GXP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-021 — Credential reset/recovery | SPEC-GXP-002 | H | yes | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-022 — No signature delegation | SPEC-GXP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-023 — Service account prohibition | SPEC-GXP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-024 — Biometric extensibility | SPEC-GXP-002 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-025 — Time source | SPEC-GXP-002 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-026 — Signer acknowledgement | SPEC-GXP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-027 — Signature receipt | SPEC-GXP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-028 — Revocation/correction handling | SPEC-GXP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-029 — Customer Part 11 certification support | SPEC-GXP-002 | H | yes | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| SIG-FR-030 — Inspection/reporting | SPEC-GXP-002 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-001 — Independent audit ledger | SPEC-GXP-003 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-002 — Automatic generation | SPEC-GXP-003 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-003 — UTC timestamp | SPEC-GXP-003 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-004 — Actor attribution | SPEC-GXP-003 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-005 — Action semantics | SPEC-GXP-003 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-006 — Old/new preservation | SPEC-GXP-003 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-007 — Changed field set | SPEC-GXP-003 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-008 — Reason linkage | SPEC-GXP-003 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-009 — Signature linkage | SPEC-GXP-003 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-010 — Record/version linkage | SPEC-GXP-003 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-011 — Correlation/causation | SPEC-GXP-003 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-012 — Source attribution | SPEC-GXP-003 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-013 — Software/rule version | SPEC-GXP-003 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-014 — Append-only application permissions | SPEC-GXP-003 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-015 — Partitioning without semantic loss | SPEC-GXP-003 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-016 — Per-record hash chain | SPEC-GXP-003 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-017 — Integrity checkpoints | SPEC-GXP-003 | H | yes | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-018 — Integrity verification job | SPEC-GXP-003 | H | yes | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-019 — Privileged DB monitoring | SPEC-GXP-003 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-020 — Audit review UI | SPEC-GXP-003 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-021 — Audit review annotations | SPEC-GXP-003 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-022 — Export | SPEC-GXP-003 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-023 — Retention | SPEC-GXP-003 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-024 — Legal/quality hold | SPEC-GXP-003 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-025 — Sensitive-data handling | SPEC-GXP-003 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-026 — Migration audit | SPEC-GXP-003 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-027 — Failed-action security trail | SPEC-GXP-003 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-028 — Time ordering | SPEC-GXP-003 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-029 — Backup/restore integrity | SPEC-GXP-003 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| AUD-FR-030 — No ordinary purge UI | SPEC-GXP-003 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-001 — Immutable released version | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-002 — Canonical snapshot | SPEC-GXP-004 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-003 — Cryptographic digest | SPEC-GXP-004 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-004 — Release metadata | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-005 — Evidence manifest | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-006 — Batch issue snapshot | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-007 — Snapshot dependency closure | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-008 — Effective dating | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-009 — Supersession | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-010 — Controlled correction | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-011 — Correction eligibility | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-012 — No silent overwrite | SPEC-GXP-004 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-013 — Void/cancel semantics | SPEC-GXP-004 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-014 — Signature binding | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-015 — Audit linkage | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-016 — Inspection retrieval | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-017 — Deterministic export | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-018 — Schema evolution | SPEC-GXP-004 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-019 — Retention class | SPEC-GXP-004 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-020 — Legal/quality hold | SPEC-GXP-004 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-021 — Archive tiering | SPEC-GXP-004 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-022 — WORM-capable evidence | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-023 — Version numbering | SPEC-GXP-004 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-024 — Content addressing | SPEC-GXP-004 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-025 — Cross-constituent snapshot | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-026 — Migration provenance | SPEC-GXP-004 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-027 — Restore verification | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-028 — Access control | SPEC-GXP-004 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-029 — Reference integrity | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| VLT-FR-030 — Disposition package | SPEC-GXP-004 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-001 — Unique human identity | SPEC-IAM-001 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-002 — External identity federation | SPEC-IAM-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-003 — Local identity fallback | SPEC-IAM-001 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-004 — User lifecycle | SPEC-IAM-001 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-005 — Role catalogue | SPEC-IAM-001 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-006 — Permission actions | SPEC-IAM-001 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-007 — Tenant scope | SPEC-IAM-001 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-008 — Site/area scope | SPEC-IAM-001 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-009 — Product/process scope | SPEC-IAM-001 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-010 — Qualification object | SPEC-IAM-001 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-011 — Training gate | SPEC-IAM-001 | H | yes | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-012 — Equipment qualification authorization | SPEC-IAM-001 | H | yes | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-013 — Signature entitlement | SPEC-IAM-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-014 — Segregation-of-duties policy | SPEC-IAM-001 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-015 — Dynamic SoD context | SPEC-IAM-001 | H | yes | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-016 — Delegation of work | SPEC-IAM-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-017 — Temporary authorization | SPEC-IAM-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-018 — Break-glass access | SPEC-IAM-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-019 — Privileged role separation | SPEC-IAM-001 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-020 — Vendor support access | SPEC-IAM-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-021 — Service accounts | SPEC-IAM-001 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-022 — Device identities | SPEC-IAM-001 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-023 — Session controls | SPEC-IAM-001 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-024 — MFA | SPEC-IAM-001 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-025 — Role assignment approval | SPEC-IAM-001 | H | yes | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-026 — Access review | SPEC-IAM-001 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-027 — Joiner/mover/leaver | SPEC-IAM-001 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-028 — Policy decision evidence | SPEC-IAM-001 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-029 — Least privilege defaults | SPEC-IAM-001 | H | yes | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-030 — No client-side authority | SPEC-IAM-001 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-031 — Qualification override | SPEC-IAM-001 | H | yes | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| IAM-FR-032 — Historical access | SPEC-IAM-001 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-001 — Controlled rule object | SPEC-GXP-006 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-002 — Rule lifecycle | SPEC-GXP-006 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-003 — Effective dating | SPEC-GXP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-004 — Deterministic evaluation | SPEC-GXP-006 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-005 — Safe expression language | SPEC-GXP-006 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-006 — Typed inputs | SPEC-GXP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-007 — Typed outputs | SPEC-GXP-006 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-008 — Unit management | SPEC-GXP-006 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-009 — Decimal arithmetic | SPEC-GXP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-010 — Rounding rules | SPEC-GXP-006 | H | yes | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-011 — Limit rules | SPEC-GXP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-012 — Eligibility rules | SPEC-GXP-006 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-013 — Sequence/progression rules | SPEC-GXP-006 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-014 — Signature rules | SPEC-GXP-006 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-015 — Deviation/exception triggers | SPEC-GXP-006 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-016 — Release rules | SPEC-GXP-006 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-017 — Yield calculation | SPEC-GXP-006 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-018 — Potency/assay adjustment | SPEC-GXP-006 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-019 — Reconciliation calculation | SPEC-GXP-006 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-020 — Time-window rules | SPEC-GXP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-021 — Decision explanation | SPEC-GXP-006 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-022 — Evaluation persistence | SPEC-GXP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-023 — Simulation/test mode | SPEC-GXP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-024 — Rule test cases | SPEC-GXP-006 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-025 — Independent verification | SPEC-GXP-006 | H | yes | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-026 — Change impact | SPEC-GXP-006 | H | no | 1 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-027 — Snapshot binding | SPEC-GXP-006 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-028 — External result rules | SPEC-GXP-006 | H | no | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-029 — Missing/invalid inputs | SPEC-GXP-006 | H | yes | 4 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-030 — Overflow/domain errors | SPEC-GXP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-031 — Rule engine versioning | SPEC-GXP-006 | H | no | 2 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |
| RUL-FR-032 — Performance/cache safety | SPEC-GXP-006 | H | no | 3 | NOT_STARTED | NOT_VERIFIED | NOT_VALIDATED |

Update the columns as work proceeds; the authoritative record is `traceability/TRACEABILITY_MASTER.csv` and `status/build-status.json`.
