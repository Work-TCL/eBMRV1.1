# WP-01 — Implementation Sequence

1. **Document 03 — GxP Mutation Gateway**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-01/03_*.md`)
2. **Document 04 — 21 CFR Part 11 Electronic Signature**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-01/04_*.md`)
3. **Document 05 — Immutable Audit Ledger & Audit Review**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-01/05_*.md`)
4. **Document 06 — Record Version Vault, Locking, Amendment & Controlled Correction**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-01/06_*.md`)
5. **Document 07 — Identity, Authorization, RBAC, Qualification & Segregation-of-Duties**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-01/07_*.md`)
6. **Document 08 — Regulatory Rules & Calculation Engine**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-01/08_*.md`)

## Per-document notes from the specifications

### Document 03
```text
1. command envelope + error registry;
2. auth/context middleware;
3. PostgreSQL command receipt;
4. optimistic concurrency utility;
5. idempotency store;
6. policy client;
7. rules client;
8. signature proof interface;
9. transaction template;
10. audit repository integration;
11. outbox;
12. first command: noncritical test aggregate;
13. first regulated command: released-master publish;
14. batch-step command;
15. integration command;
16. failure-injection test suite.
```
### Document 04
```text
1. policy/config schema;
2. challenge table;
3. OIDC validation;
4. Keycloak reference integration;
5. record target/hash verification;
6. replay/expiry;
7. signature table;
8. consume contract;
9. multi-signature;
10. UI component;
11. export manifestation;
12. negative/attack tests.
```
### Document 05
```text
1. event schema;
2. partitioned table;
3. insert repository;
4. old/new diff normalizer;
5. aggregate sequence;
6. canonical hash;
7. query API;
8. review UI;
9. checkpoint manifest;
10. integrity verifier;
11. export;
12. retention/archive;
13. privileged-access monitoring integration.
```
### Document 06
```text
1. canonicalization package;
2. digest test vectors;
3. vault table;
4. release API/domain service;
5. version query;
6. evidence manifest;
7. snapshot builder;
8. correction workflow;
9. export metadata;
10. retention/archive;
11. restore/integrity tests.
```
### Document 07
```text
1. subject mapping;
2. JWT/OIDC validation;
3. role/scope tables;
4. policy evaluation framework;
5. qualifications;
6. training integration;
7. SoD history checks;
8. signature entitlement;
9. temporary auth;
10. break-glass;
11. access review;
12. Keycloak reference deployment.
```
### Document 08
```text
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
```
