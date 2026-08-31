# WP-12 — Dependencies

**Upstream work packages:** WP-01, WP-11

## Entry conditions

- All upstream work packages have passed `11_ACCEPTANCE_CHECKLIST.md`.
- Contracts for in-scope modules committed (Document 113).
- Approved baselines 106–115 available in `specs/Documents_106_115/`.

## Platform services consumed

- Mutation Gateway, Policy/IAM, Signature, Audit, Vault, Rules (WP-01)
- Outbox/NATS, PostgreSQL, evidence store (WP-11)
- Security controls (WP-10)

## Downstream consumers

- WP-13: AI Advisory Capabilities
- WP-14: Customer Deployment / PQ / Go-Live
