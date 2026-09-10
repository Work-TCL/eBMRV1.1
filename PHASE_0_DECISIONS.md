# Phase 0 — Architecture & Scope Decisions

**Date:** 2026-09-09
**Decider:** Project Owner (recorded via working session)
**Context:** `DOCS_VS_IMPLEMENTATION_GAP_ANALYSIS.md` §8 / §10 — Phase 0 is the set of `DO NOT GUESS`
decisions that gate all downstream remediation.

---

## 1. Decisions made this pass

| # | Question | Decision | Recorded in |
|---|---|---|---|
| D1 | Two live authoritative stores for Product / Recipe / Batch (SG‑173) | **Retire the day‑one scaffolds** (`app/modules/product`, `recipe`, `batch`). `product_master` / `recipe_master` / `batch_execution` are the sole authoritative stores. Cut over all three now while the live DB holds near‑zero data. Delete the 5 demo rows via a controlled repair migration. | **ADR‑0013** · SG‑173 → RESOLVED · SG‑149 → PARTIALLY_RESOLVED · SG‑162 → DIRECTION_DECIDED |
| D2 | ADR‑0008 says Frappe is the operator UI of record; reality is the Next.js `frontend/` (72 pages), and `apps/ebmr_frappe` was never built | **Supersede ADR‑0008.** The Next.js `frontend/` is the operator UI of record, in scope for GxP UI validation. It reads the GxP API directly — there is no Frappe/MariaDB projection tier. | **ADR‑0010** · SG‑021 → RESOLVED · new **SG‑182** (Document 71 rework/descope) |
| D3 | NATS/JetStream (Doc 73) and Temporal (Doc 74) are specified but only stand‑ins exist | **Build both.** In WP‑11, NATS/JetStream first, then Temporal, contract‑first. Current in‑process outbox publisher + `workflowops` are interim only; the validation package must not claim NATS/Temporal until built. | **ADR‑0011** · new **SG‑183** |
| D4 | Full‑scope qualification is ~1 year; what does the first `QUALIFIED`/`RELEASED` milestone target? | **Narrow core‑eBMR (M1).** WP‑01 (GxP core) + WP‑02 (product/recipe/batch) + WP‑03 (genealogy/review/release/packaging/yield) + WP‑04 (materials/QC) + WP‑10 security **baseline only**. WP‑05/06/07/08/09/13 follow as later validated increments. WP‑11 / WP‑12 are continuous, not deferred. | **ADR‑0012** |

**New ADRs:** `ebmr-edhr/docs/adr/ADR-0010-nextjs-operator-ui-of-record.md`,
`ADR-0011-event-transport-and-durable-workflow.md`,
`ADR-0012-first-qualified-release-scope.md`,
`ADR-0013-single-authoritative-store-product-recipe-batch.md`.

**Already settled by earlier ADRs (no action needed):** ADR‑0006 (single‑tenant per deployment;
`assert_single_organization` guard), ADR‑0007 (Python/FastAPI supersedes the frozen TS/Node ADR‑010),
ADR‑0009 (WP‑07 consolidated service + provisional `erp.*` schema, SG‑121).

---

## 2. SPEC_GAP register updates (`ebmr-edhr/docs/generated/18_SPEC_GAPS.md`)

| Gap | Was | Now |
|---|---|---|
| SG‑021 | OPEN — frontend retirement timing undecided | **RESOLVED** — `frontend/` is the UI of record, not retired (ADR‑0010) |
| SG‑173 | OPEN — two live stores for product/recipe/batch | **RESOLVED** — ADR‑0013, Option A, all three entities |
| SG‑149 | OPEN — `ebmr.batches` vs `ebmr.gxp_batch` | **PARTIALLY_RESOLVED** — architectural half decided (`gxp_batch` authoritative); PFS‑FR‑020 still unimplemented, off the M1 path |
| SG‑162 | OPEN — `service_identity` exists twice | **DIRECTION_DECIDED** — fold Edge credential store into the Doc 62 registry during the SG‑173 cutover |
| SG‑182 | — | **NEW / OPEN** — Document 71 (Frappe projection architecture) needs human rework or formal descope |
| SG‑183 | — | **NEW / OPEN** — NATS + Temporal build tracked as a WP‑11 task per ADR‑0011 |
| SG‑028 / SG‑034 / SG‑036 | "Frappe UI surface can't be built — `apps/ebmr_frappe` doesn't exist" | Re‑scoped by ADR‑0010 — the equivalent `frontend/` screens exist; these become "confirm the existing screen covers the requirement" |

---

## 3. Phase 0 items still requiring a Quality / Regulatory sign‑off

These are **regulated decisions** (`class R` in the gap register). They cannot be made by engineering or
by this project's SPEC_GAP process — they need the customer's Head of Quality / Regulatory Affairs /
Security Officer as noted. For each, the register already lays out the options; what's needed is a signed
decision that becomes a Document 106 / 107 / 108 / 109 / 110 addendum row.

### Needed before M1 validation execution can start (ADR‑0012 entry criteria)

| Gap | Decision needed | Approver |
|---|---|---|
| **SG‑143 + SG‑145** | Ratify Document 110 §2's calculation‑class table (currently marked "(PROPOSED)"), so the rules evaluator can apply the frozen unit / precision / rounding policy it releases. | Head of Quality + Rules Engine Owner |
| **SG‑035** (remainder) | Document 106 signature rows for the WP‑01 signed actions still failing closed: `vault_object/release`, `record_correction/complete`, `rule/release`, `product_version/{suspend,reinstate}`. | Head of Quality + Product Owner |
| **SG‑181** (remainder) | The "every performer on the batch" independence half of IND‑002/003 for QA review/release — needs a data source decision or a documented acceptance that it stays unenforced. | Head of Quality |
| **SG‑141** | Signature meaning `Disposition` is in production use (material/QC) but is not in Document 04's SIG‑FR‑003 catalogue — approve it as a customer extension or replace it with a catalogued meaning. | Head of Quality |
| **SG‑134 / SG‑135 / SG‑137** | Yield (WP‑03, in M1): the "applicable waiver/profile rule" concept, the controlled loss‑reason/category catalogue, and the owner/format/signature policy for the final batch‑record export. | Head of Quality + Product Owner |
| **SG‑163 / SG‑164** | Numeric security baselines the M1 security controls exercise: application session idle + absolute timeout; API rate‑limit, webhook replay‑window, upload byte‑cap. | Security Officer + Product Owner (per deployment) |

### Needed for later increments (not M1‑blocking)

| Gap | Decision needed | Approver |
|---|---|---|
| SG‑138 (remaining 24 pairs) | Document 106 signature rows for the WP‑05 QMS record‑type/action transitions still unsatisfiable. | Head of Quality + Regulatory Affairs |
| SG‑167 | Document 106 rows for the SPEC‑AI‑001 signed AI‑governance functions (currently zero). | Head of Quality |
| SG‑156 / SG‑160 / SG‑165 / SG‑170 | Unresolved / unimplementable signer classes: postmarket signal actions; Document 60 actions (incl. a 2‑signature requirement that can't be satisfied as written); Document 68 vulnerability‑exception approver; validation‑summary‑report generator. | Head of Quality + Regulatory Affairs / Security Officer |
| SG‑158 / SG‑159 | Federal‑holiday calendar for WORK_DAY regulatory deadlines; eMDR / E2B transport mapping + a reachable submission gateway. | Regulatory Affairs |
| SG‑087 / SG‑099 | Training assessment attempt limit + retry backoff; risk‑level‑tiered acceptance‑authority escalation matrix. | Head of Quality |
| SG‑136 | Whether an ERP/WMS inventory mismatch should raise a QA hold. | Head of Quality + Platform Architect |
| SG‑166 | Upload‑size cap and cache lag / saturation thresholds for WP‑11 (also a dependency of the NATS build). | SRE Lead + Product Owner |

---

## 4. What happens next

**Phase 0 is complete for the decisions engineering can capture.** The Quality/Regulatory items in §3
are handed to the customer Quality organisation as a batch — they do not block Phase 1 or Phase 2, and
the M1‑blocking subset is the input to WP‑12 execution, not to the build.

Proceed to:

1. **Phase 1 — reconcile status & traceability with reality** (WP‑10/11/12/13/14 code exists but is
   tracked as `NOT_STARTED`); stand up the test DB and run the 1 159 backend tests for a real baseline.
2. **Phase 2 — WP‑00 engineering backbone** (CI, SBOM, coding‑standard enforcement, branch protection).
3. **Phase 3 — execute the Phase 0 decisions in code**: the ADR‑0013 store cutover (starting with the
   independent `delete_site()` guard fix), SG‑013 contracts + `expected_version`, the M1 signature‑policy
   seeding once §3's rows are signed.

See `DOCS_VS_IMPLEMENTATION_GAP_ANALYSIS.md` §10 for the full sequence.
