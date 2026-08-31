# WP-01 — Dependencies

**Upstream work packages:** WP-00

## Entry conditions

- All upstream work packages have passed `11_ACCEPTANCE_CHECKLIST.md`.
- Contracts for in-scope modules committed (Document 113).
- Approved baselines 106–115 available in `specs/Documents_106_115/`.

## Platform services consumed

- Mutation Gateway, Policy/IAM, Signature, Audit, Vault, Rules (WP-01)
- Outbox/NATS, PostgreSQL, evidence store (WP-11)
- Security controls (WP-10)

## Downstream consumers

- WP-02: Product / Recipe / Batch Execution
- WP-05: Quality Management System
- WP-07: Enterprise Integrations
- WP-10: Security
- WP-11: Data / Infrastructure / DR / SRE
- WP-12: Validation Platform & Evidence
- WP-13: AI Advisory Capabilities
