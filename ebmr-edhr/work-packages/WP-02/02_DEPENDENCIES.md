# WP-02 — Dependencies

**Upstream work packages:** WP-01

## Entry conditions

- All upstream work packages have passed `11_ACCEPTANCE_CHECKLIST.md`.
- Contracts for in-scope modules committed (Document 113).
- Approved baselines 106–115 available in `specs/Documents_106_115/`.

## Platform services consumed

- Mutation Gateway, Policy/IAM, Signature, Audit, Vault, Rules (WP-01)
- Outbox/NATS, PostgreSQL, evidence store (WP-11)
- Security controls (WP-10)

## Downstream consumers

- WP-03: Genealogy / Review / Release / Packaging / Yield
- WP-04: Procurement / Materials / QC
- WP-05: Quality Management System
- WP-06: Equipment / Sterile / Edge
- WP-08: DDCP Product Profiles
