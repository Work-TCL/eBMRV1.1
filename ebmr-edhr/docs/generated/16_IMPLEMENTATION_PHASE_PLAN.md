# 16 — Implementation Phase Plan

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Dependency-ordered executable work packages with gates and acceptance.

---

## Gates (Master Index §9)

- **Gate A** — Documents 03–08 understood and implemented before regulated application modules.
- **Gate B** — Documents 09–15 provide the minimum eBMR execution/review/release backbone.
- **Gate C** — Documents 16–60 complete the DDCP V1 functional scope.
- **Gate D** — Documents 61–96 provide security, infrastructure, validation and pilot readiness.
- **Gate E** — Documents 97–105 enforced continuously during development and release.

## Work packages

| WP | Title | Source documents | Depends on | Requirements | Entry gate | Exit gate |
|---|---|---|---|---|---|---|
| WP-00 | Repository, Tooling & Contract Foundations | 01, 02, 97, 98, 99, 100, 101, 102, 103, 104 | — | 542 | Phase 0 review approved | `work-packages/WP-00/11_ACCEPTANCE_CHECKLIST.md` fully satisfied |
| WP-01 | GxP Core — Mutation / Signature / Audit / Vault / IAM / Rules | 03, 04, 05, 06, 07, 08 | WP-00 | 186 | all listed dependencies accepted | `work-packages/WP-01/11_ACCEPTANCE_CHECKLIST.md` fully satisfied |
| WP-02 | Product / Recipe / Batch Execution | 09, 10, 11, 12 | WP-01 | 134 | all listed dependencies accepted | `work-packages/WP-02/11_ACCEPTANCE_CHECKLIST.md` fully satisfied |
| WP-03 | Genealogy / Review / Release / Packaging / Yield | 13, 14, 15, 16, 17 | WP-02 | 156 | all listed dependencies accepted | `work-packages/WP-03/11_ACCEPTANCE_CHECKLIST.md` fully satisfied |
| WP-04 | Procurement / Materials / QC | 18, 19, 20, 21, 22, 23, 24, 25 | WP-02 | 272 | all listed dependencies accepted | `work-packages/WP-04/11_ACCEPTANCE_CHECKLIST.md` fully satisfied |
| WP-05 | Quality Management System | 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37 | WP-01, WP-02 | 257 | all listed dependencies accepted | `work-packages/WP-05/11_ACCEPTANCE_CHECKLIST.md` fully satisfied |
| WP-06 | Equipment / Sterile / Edge | 38, 39, 40, 41, 42, 43, 44, 45, 46, 47 | WP-02, WP-04 | 284 | all listed dependencies accepted | `work-packages/WP-06/11_ACCEPTANCE_CHECKLIST.md` fully satisfied |
| WP-07 | Enterprise Integrations | 48, 49, 50, 51, 52, 53 | WP-01, WP-04 | 161 | all listed dependencies accepted | `work-packages/WP-07/11_ACCEPTANCE_CHECKLIST.md` fully satisfied |
| WP-08 | DDCP Product Profiles | 54, 55, 56, 57 | WP-02, WP-03, WP-06 | 120 | all listed dependencies accepted | `work-packages/WP-08/11_ACCEPTANCE_CHECKLIST.md` fully satisfied |
| WP-09 | Postmarket | 58, 59, 60 | WP-05 | 98 | all listed dependencies accepted | `work-packages/WP-09/11_ACCEPTANCE_CHECKLIST.md` fully satisfied |
| WP-10 | Security | 61, 62, 63, 64, 65, 66, 67, 68 | WP-00, WP-01 | 232 | all listed dependencies accepted | `work-packages/WP-10/11_ACCEPTANCE_CHECKLIST.md` fully satisfied |
| WP-11 | Data / Infrastructure / DR / SRE | 69, 70, 71, 72, 73, 74, 75, 76, 77, 78 | WP-00, WP-01 | 315 | all listed dependencies accepted | `work-packages/WP-11/11_ACCEPTANCE_CHECKLIST.md` fully satisfied |
| WP-12 | Validation Platform & Evidence | 79, 80, 81, 82, 83, 84, 86, 88, 89, 90, 91, 92, 93, 94, 96 | WP-01, WP-11 | 350 | all listed dependencies accepted | `work-packages/WP-12/11_ACCEPTANCE_CHECKLIST.md` fully satisfied |
| WP-13 | AI Advisory Capabilities | 105 | WP-01, WP-10, WP-12 | 56 | all listed dependencies accepted | `work-packages/WP-13/11_ACCEPTANCE_CHECKLIST.md` fully satisfied |
| WP-14 | Customer Deployment / PQ / Go-Live | 85, 87, 95 | WP-12 | 66 | all listed dependencies accepted | `work-packages/WP-14/11_ACCEPTANCE_CHECKLIST.md` fully satisfied |

## Execution order
```text
WP-00  Repository, Tooling & Contract Foundations
WP-01  GxP Core — Mutation / Signature / Audit / Vault / IAM / Rules
WP-02  Product / Recipe / Batch Execution
WP-03  Genealogy / Review / Release / Packaging / Yield
WP-04  Procurement / Materials / QC
WP-05  Quality Management System
WP-06  Equipment / Sterile / Edge
WP-07  Enterprise Integrations
WP-08  DDCP Product Profiles
WP-09  Postmarket
WP-10  Security
WP-11  Data / Infrastructure / DR / SRE
WP-12  Validation Platform & Evidence
WP-13  AI Advisory Capabilities
WP-14  Customer Deployment / PQ / Go-Live
```

WP-10 (Security), WP-11 (Data/Infrastructure) and WP-12 (Validation) are **continuous**: they start with WP-00/WP-01 and remain active through every later package. They are listed as packages so that their deliverables are explicitly owned, not to defer them to the end.
