# 31 — Validated-State Change & Revalidation Matrix

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** What changes, what it triggers, and what evidence is required (Document 96).

---

| Change type | Examples | Impact assessment | Revalidation scope | Approval |
|---|---|---|---|---|
| Platform code — higher-risk module | Mutation Gateway, signature, audit, release | mandatory | targeted OQ + regression + Part 11 re-verification | Validation Lead + Head of Quality |
| Platform code — standard-risk module | reporting, dashboards | mandatory (lightweight) | automated regression + risk-based OQ sample | Validation Lead |
| Signature policy change (Doc 106) | new signature point, changed meaning | mandatory | Part 11 OQ for affected actions | Head of Quality |
| SoD rule change (Doc 107) | new prohibited pair, independence rule | mandatory | authorization OQ negative tests | Head of Quality + Security Officer |
| Retention class change (Doc 108) | duration, trigger, hold behaviour | mandatory | data-integrity qualification (Doc 89) | Head of Quality + Legal |
| Calculation policy change (Doc 110) | rounding stage, precision | mandatory | boundary + recomputation tests (Doc 84) | Head of Quality |
| Schema/migration on regulated table | new column, backfill | mandatory | migration validation (Doc 87) + reconciliation | Data Architect + Validation Lead |
| API/event contract breaking change | new schema_version | mandatory | interface validation (Doc 90) + consumer regression | Platform Architect |
| Infrastructure change | K8s version, DB version, storage class | mandatory | infrastructure qualification (Doc 86) + DR re-test if tier affected | SRE Lead + Validation Lead |
| Customer configuration | workflow, roles, product profile, rules | mandatory | PQ/UAT for affected process (Doc 85) | Customer Quality |
| Dependency upgrade | library, base image | mandatory (SBOM/licence + security) | regression + security qualification if control-bearing | Security Officer + Validation Lead |
| AI use case change (Doc 105) | model, prompt, tool allowlist, retrieval source | mandatory | AI evaluation set + security tests; authority boundary re-verified | Head of Quality + Security Officer |

## Periodic review triggers
- Scheduled interval per Document 96.
- Accumulated change volume above threshold.
- Recurring deviations or CAPA in the same function.
- Regulatory change affecting a predicate rule cited in 21_REGULATORY_OBLIGATION_MATRIX.md.
