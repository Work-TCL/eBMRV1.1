# eBMR / eDHR — Docs vs. Implementation Gap Analysis

**Date:** 2026-09-09
**Reference baseline:** `ebmr-edhr/` (Documents 01–105 + addenda 106–115, authoring standards, 15 work packages, 103 tracked modules, 2 965 requirements, 9 150 test cases, SPEC_GAP register SG-001…SG-181)
**Implementation reviewed:**
- Backend — `services/gxp-api/` (FastAPI + async SQLAlchemy 2.0 + Alembic; one consolidated service; ~45 domain modules; **757 HTTP endpoints**; **93 Alembic migrations**, head `a6d525b2d585` / `0093`; 1 159 pytest tests)
- Frontend — `frontend/` (Next.js App Router SPA, **72 pages**, custom ported design system, calls the GxP API directly on `:8010`)

> Scope note: this is a consolidation of the project's own tracking artefacts (`status/`, `traceability/`, `docs/generated/18_SPEC_GAPS.md`, `docs/generated/42_CAPABILITY_COVERAGE_MATRIX.csv`) **cross-checked against the actual code tree**, not an independent line-by-line re-verification of 2 965 requirements. Where the tracking files disagree with the code, that is called out — it is itself a finding.

---

## 1. Executive summary

| Dimension | State |
|---|---|
| Modules started | 83 / 103 |
| Modules `REVIEWED` / `OQ_EXECUTED` / `QUALIFIED` / `RELEASED` | **0 / 0 / 0 / 0** |
| Requirements `VERIFIED` | 763 / 2 965 (~26 %) |
| Requirements `IN_PROGRESS` / `BLOCKED` / `DEFERRED` / `NOT_STARTED` | 623 / 326 / 82 / 1 169 |
| Test-case library executed & passing | 2 503 / 9 150 (27 %) |
| Test-case library `BLOCKED` (on SPEC_GAPs) | 2 269 (25 %) |
| Test-case library `NOT_STARTED` | 3 708 (41 %) |
| Open SPEC_GAPs | ~170 of 181 (SG-001…011 closed by addenda) |
| Currently **blocking** SPEC_GAPs | SG-013, SG-138, SG-143, SG-167 (+ SG-173 as the lynchpin) |

**Bottom line.** A large, genuinely substantive implementation exists — most functional domains have a working command path, endpoints and a UI. But:

1. **Nothing is validated.** No module has passed CODE_COMPLETE. The entire validation work package (WP-12: IQ/OQ/PQ, VMP, traceability, go-live) is built as code but has **zero executed evidence**, so no module can legally reach `QUALIFIED`/`RELEASED`.
2. **The architecture diverged from the frozen baseline** in ways that are defensible but not all formally recorded (Next.js instead of Frappe Desk; Python/FastAPI instead of TS/Node; no NATS/Temporal; one service instead of the Document 02 split).
3. **Data authority is violated in several places** (SG-173 / SG-149 / SG-180 / SG-162 — duplicate live stores for product, recipe, batch, batch-steps, service identity).
4. **Contract-first was not followed** (SG-013): contracts were back-derived, event schemas are incomplete, and no operation implements optimistic concurrency (`expected_version`, SG-014).
5. **Signature-policy data (Document 106) is incomplete** — dozens of regulated transitions are still unsatisfiable (SG-138, SG-035, SG-167, SG-157/160/161/165/170).
6. **Status/traceability records are stale** — WP-10/11/12/13/14 have real code that the tracking files still show as `NOT_STARTED` with 0 verified requirements.

---

## 2. Architecture-level deviations from the spec baseline

These are not "bugs" but they change what "complete against the docs" means, and each needs an ADR or SPEC_GAP as `REMEDIATION_R1.md` FIX 4 already demanded.

| # | Baseline says | Implementation is | Consequence / what's owed |
|---|---|---|---|
| A1 | Frappe Framework is the UI/application framework; Document 71 = Frappe/MariaDB projections (MDB-FR-001…028), Document 04 §… read-model rules | Next.js SPA reading the GxP API directly; no Frappe Desk operator UI; MariaDB projection layer not built as specified | **Document 71 is effectively unimplemented as written.** Needs `ADR-0008` + a SPEC_GAP against Doc 71 (per REMEDIATION_R1). `eBMR-ui/` third UI directory still present. |
| A2 | ADR-010 (frozen): TypeScript / Node.js LTS for GxP services | Python 3.12 + FastAPI + async SQLAlchemy | Needs `ADR-0007` (superseding ADR-010); Doc 97 coding-standards matrix (`33_…`) must name Python tooling (ruff/mypy). |
| A3 | Document 02 §11 logical service split (mutation, signature, audit, IAM, rules, per-domain services) | One consolidated `services/gxp-api` process | Allowed as *deployment* consolidation, but module-boundary discipline (no cross-module repo/table access) is enforced only by convention, not by build/lint. |
| A4 | AG-09 — PostgreSQL outbox is source, **NATS/JetStream** is transport (Document 73, EVT-FR-001…030) | In-process `asyncio` outbox-publisher loop with a stand-in publisher; no NATS | Doc 73 transport requirements unmet; SG-166 numeric baselines open. Either build NATS or formally descope with a SPEC_GAP. |
| A5 | AG-10 — **Temporal** orchestrates workflows (Document 74, TMP-FR-001…030) | `workflowops` stand-in module; no Temporal runtime | Doc 74 unimplemented; durable-workflow / replay test requirements (TEST-FR-010) cannot be met. |
| A6 | AG-05 — one authoritative store per regulated entity | **Two live stores** for Product, Recipe, Batch (`ebmr.*` legacy vs `gxp_*`) — SG-173; `ebmr.batches` vs `ebmr.gxp_batch` — SG-149; generic batch-steps vs DDCP execution records — SG-180; `service_identity` twice — SG-162; qualification in `iam.qualifications` vs `qms.qualification_record` — SG-086 | **SG-173 is the lynchpin.** It blocks the SG-013 event-schema closure and keeps WP-02 heavily `BLOCKED`. Migration/cutover plan is reserved for the project owner. |
| A7 | Contract-first: OpenAPI 3.1 / AsyncAPI committed **before** implementation (Doc 101/113, CTR-FR-001) | Contracts back-derived after code; `contracts/openapi/` + `contracts/events/` partial; WP-02 events uncontracted; **no operation declares `expected_version`** (SG-014) | SG-013 remains blocking. Optimistic concurrency (MUT-FR-009, CTR-FR-009) is untested and likely absent on most aggregates. |

---

## 3. Where each work package actually stands

Legend: **Built** = code + endpoints exist · **Verified** = requirements marked VERIFIED in tracking · **Gate** = formal stage.

| WP | Title | Gate (tracking) | Reqs verified | Reality check |
|---|---|---|---|---|
| **WP-00** | Repo / tooling / contract foundations (Docs 97–104) | NOT_STARTED | 10 / 278 | **Largely not done.** Only the SG-013 contract slice (`contracts/`, `tooling/contracts`, `tooling/events`) is partial. Missing: CI/CD release process (Doc 103 / `39_`), SBOM + licence register (Doc 104 / `40_`), coding-standard enforcement matrix (Doc 97 / `33_`), branching standard (Doc 99). This is the validation backbone. |
| **WP-01** | GxP core — mutation / signature / audit / vault / IAM / rules | IN_DEVELOPMENT | 34 / 186 | Kernel built (`app/mutation/gateway.py`, signature service, audit ledger + hash chain, vault, IAM). 52 reqs BLOCKED, 71 IN_PROGRESS. Gaps: MUT-FR-023/024/026 (integration/device identity, privileged repair), SG-038/039/040 (reason enforcement, admin-repair command, inspection endpoints), SG-041/042 (signature meaning catalogue, identity-verification evidence). |
| **WP-02** | Product / recipe / batch execution / eDHR | IN_DEVELOPMENT | 11 / 134 · **86 BLOCKED** | Most-blocked functional WP. Blocked on SG-043–050 (prose-only entities: `recipe_material_requirement`, `recipe_equipment_requirement`, `gxp_step_result`, device-usage/test/defect tables) and **SG-173**. Recent partial fixes: SG-047/048 (step results, step holds, `production_complete` state), SG-178 (step `required_role_code` now enforced on the regulated path), SG-035 (recipe/product release signatures). Material/equipment linkage at step start still deferred (SG-045). |
| **WP-03** | Genealogy / review / release / packaging / yield | IN_DEVELOPMENT | 32 / 156 · 65 BLOCKED | Engines exist. Gaps: SG-051/052 (impact-assessment & export entities; no real domain-event producers), SG-053/054 (`qa_review_item`/`qa_review_comment` prose-only), SG-055/056 (non-batch release scope; packaging reconciliation entities missing, API list incomplete), SG-132–137 (yield: waiver/profile rule, loss-category catalogue, eDHR export owner — several reserved for project owner). SG-181 wired QA-review / release-scope signatures (partial — "every performer" independence half has no data source). |
| **WP-04** | Procurement / materials / QC | IN_DEVELOPMENT | **166 / 272** (best-covered) | Strongest functional area. Still open: SG-057 (material-specification-version entity missing — root cause for ~8 reqs), SG-066/070/074 (QC method master, OOS/OOT wiring, retest-count policy), SG-075 (`material_lot` disposition signature mismatch vs Doc 106 rows 44/45), SG-081 (`warehouse_location` CRUD — partially resolved read + create only), SG-082–085 (barcode, storage-condition monitoring, ERP reconciliation, cycle-count freeze), SG-091–096 (dispensing: reason enforcement, signed-create pattern, balance/edge adapter, tolerance authority, conditional independence). |
| **WP-05** | Quality Management System (Docs 26–37) | IN_DEVELOPMENT | 129 / 257 · 56 BLOCKED | All 12 QMS modules built with endpoints + UI. **SG-138 blocking**: of 26 QMS record-type/action pairs needing Doc 106 signature rows, only `deviation_record`/disposition+close is resolved — **24 still unsatisfiable**. Plus SG-059–108: cross-module wiring almost entirely absent (auto candidate creation, release-eligibility gating, NCR→CAPA auto-create, SCAR→supplier-status→receipt gate, retraining-on-release), no notification/escalation worker (SG-062/090/100/108), metric-family calculations are caller-supplied not computed (SG-107), complainant PII is plain RBAC-gated JSONB (SG-104). |
| **WP-06** | Equipment / sterile / edge (Docs 38–47) | NOT_STARTED (formal) | 130 / 284 · **47 NOT_STARTED** | Equipment/cleaning/EM/sterilisation/aseptic **are** built and mostly verified. **Three edge modules truly not started:** SPEC-EDGE-002 (Doc 44 industrial device protocol drivers), SPEC-EDGE-003 (Doc 45 store/forward offline buffering), SPEC-EDGE-004 (Doc 46 barcode/scanner/balance/printer peripherals). SPEC-EDGE-001/005 in dev but blocked (SG-118–120, SG-127–131). SG-109–117 block the equipment modules' final verification. SG-176/177 added create/list/supersede for `aseptic_profile_version` and `equipment_area` (were missing from the spec API lists). |
| **WP-07** | Enterprise integrations (Docs 48–53) | IN_DEVELOPMENT | 145 / 161 | High code coverage (ERP/ERPNext/SAP/Dynamics adapters, LIMS, reconciliation). **All 6 modules flagged BLOCKED** by SG-121–126 (integration contract/identity/reconciliation baseline questions) and SG-151–153 (no manifest/checksum rule for the SFTP/CSV/XML/EDI adapter; no real external ERP DB schema for the direct-DB adapter; **no Document 104 dependency justification for a SOAP or SFTP client**). |
| **WP-08** | DDCP product profiles (Docs 54–57) | IN_DEVELOPMENT | 32 / 120 · 80 IN_PROGRESS | PFS / autoinjector / inhalation / coated-device profiles built on a **provisional schema** (SG-150 — Docs 55/56/57 have no Document 112 approved schema). SG-179 (PFS bulk drug/biologic batch reference has no supporting capability — DRUG/BIOLOGIC constituent hand-offs can't be accepted). SG-180 (DDCP execution records and generic batch-steps don't sync). Frontend missing screens for `handoff-decide`, `fill-sub-actions`, `assembly-verify`; batch-readiness view missing a query param. |
| **WP-09** | Postmarket (Docs 58–60) | **CODE_COMPLETE** | 24 / 98 | Built. Open: SG-154 (`postmarket_source` field-set conflict Doc 58 vs 112), SG-155 (no signal-rule formula in baseline), SG-156 (Doc 106 rows 120–122 signer class "per policy lookup" unresolved), SG-157 (no signature policy for `reportability_track.decide` / `regulatory_report.approve`), SG-158 (no federal-holiday calendar for WORK_DAY deadlines), SG-159 (no eMDR/E2B transport mapping or gateway), SG-160 (Doc 60 actions incl. an unimplementable 2-signature requirement). |
| **WP-10** | Security (Docs 61–68) | **CODE_COMPLETE** | 50 / 232 · 161 IN_PROGRESS | All 8 SEC modules built (threat model, IAM security, PAM/break-glass, appsec runtime, crypto/PKI, network/zero-trust, incident/forensics, secure SDLC/SBOM). Verification thin. Open: SG-161 (Doc 61 signature-shaped endpoints unresolved), SG-162 (duplicate `service_identity`), SG-163 (session idle/absolute timeout has no approved number — placeholder in `config.py`), SG-164 (rate-limit / webhook-replay / upload-cap numbers), SG-165 (vuln-exception approver role unresolvable). |
| **WP-11** | Data / infra / DR / SRE (Docs 69–78) | NOT_STARTED (formal) | **0 / 315** | **Tracking is wrong.** Code exists: `dataops`, `dbops` (partitioning, concurrency, read-routing, integrity), `disaster_recovery` (failover, recovery), `readmodels` (cache, search), `sre` — plus test files (`test_dbops_pg_architecture.py`, `test_disaster_recovery.py`, `test_sre_slo_capacity.py`, `test_readmodels_cache_search.py`). Never traced/verified/status-updated. Doc 71 (Frappe projections) and Doc 73/74 (NATS/Temporal) not built as specified (see §2). SG-166 (upload cap / cache-lag / saturation thresholds) open. |
| **WP-12** | Validation platform & evidence (Docs 79–96) | IN_DEVELOPMENT | **0 / 350** | **Tracking is wrong** — `app/modules/validation` has **86 endpoints** + `router_wp14` + 4 WP-12 test files + migration commands. But **no requirement is VERIFIED and no validation evidence is recorded.** This is the gate: until IQ/OQ/PQ, VMP/CSA, requirements-traceability, defect/deviation remediation and validation-summary/go-live are *executed*, **no module can pass `REVIEWED` → `QUALIFIED` → `RELEASED`.** SG-169 (PDF dependency — resolved, ReportLab), SG-170 (VSR signer class unresolvable — built unsigned), SG-172 (router was unwired — resolved). |
| **WP-13** | AI advisory (Doc 105) | IN_DEVELOPMENT | **0 / 56** | `ai_governance` module built (24 endpoints, `test_ai_governance.py`), router wired (SG-171 resolved). **SG-167 blocking**: Document 106 has **zero SPEC-AI-001 signature-policy rows**, so all 5 signed AI-governance functions are unsatisfiable. No evaluation sets / acceptance thresholds / adversarial (prompt-injection, exfiltration) test evidence recorded (AI-FR-022–025). |
| **WP-14** | Customer deployment / PQ / go-live (Docs 83/85/87/95 slice) | IN_DEVELOPMENT | **0 / 66** | `router_wp14` (20 endpoints) + 3 test files exist. Depends on WP-12 execution; nothing verified. |

---

## 4. Cross-cutting requirement gaps (platform-wide)

| Area | Gap | Requirement / SPEC_GAP |
|---|---|---|
| **Electronic signature (Doc 04/106)** | ~24 QMS transitions still have no policy row; Doc 06/08 actions (`vault_object/release`, `record_correction/complete`, `rule/release`, `product_version/{suspend,reinstate}`) unresolved; all AI signed functions unresolved; postmarket + several security/validation signers unresolved. `reason_required` column enforced by **zero** command handlers. Signature meaning `Disposition` used in production but not in the Doc 04 catalogue. | SIG-FR-004, MUT-FR-011 · SG-138, SG-035, SG-167, SG-157/160/161/165/170, SG-091, SG-141 |
| **Calculation precision (Doc 110)** | Rules evaluator **ignores** the `unit_policy` / `precision_policy` / `rounding_policy` it freezes into the Vault at release. Doc 110 §2 calc-class table is still marked "(PROPOSED)". No controlled UOM expand→migrate→contract programme; free-text UOM columns unchanged. No UOM-conversion engine anywhere. | CALC-FR-001…, DATA-FR-019 · **SG-143 (blocking)**, SG-145, SG-146, SG-077/093/133 |
| **Audit (Doc 05)** | Audit `action` vocabulary is unconstrained — no enum/registry/constraint enforces AUD-FR-005 stable event types. Integrity checkpoints / scheduled verification job (AUD-FR-017/018) partial. | AUD-FR-005/017/018 · SG-142, SG-029–033 |
| **API / event contracts (Doc 101/113)** | Three divergent error-envelope definitions; the built one omits `correlation_id`. Some command payloads lack `additionalProperties:false` (`SimulateRuleRequest`). WP-02 events uncatalogued; ~170 event types across the platform still have no committed schema. **No operation declares `expected_version`** → optimistic concurrency untested. | CTR-FR-006/009, MUT-FR-009, EVT-FR-001 · **SG-013 (blocking)**, SG-014, SG-139/140/144, SG-174 (event-name collisions) |
| **Tenancy (Doc 66/70)** | Single-tenant (Option A) chosen with an `assert_single_organization` startup guard; **row-level tenant scoping not implemented** — isolation is transitive through `site_id`. Acceptable only for per-customer deployment; must be restated as a validated limitation. | DATA-FR-020, MUT-FR-003 · REMEDIATION_R1 FIX 2 |
| **Qualification / training gate** | The platform-wide training/qualification execution gate is **not wired into any other module's Mutation Gateway calls**. Two qualification stores (`iam.qualifications` vs `qms.qualification_record`). | MUT-FR-007, TRN-FR-010/016 · SG-088, SG-086 |
| **Cross-module workflow wiring** | Deviations/NCR/OOS not wired into release eligibility; NCR→CAPA and OOS→CAPA auto-creation absent; SCAR source-suspension doesn't write `supplier.status` or gate receipt; no automatic quality-event candidate creation; no notification/escalation worker infrastructure at all. | DEV-FR-002/022, NCR-FR-012, SCAR-FR-011, etc. · SG-059/060/067/097/100/108, SG-062/090 |
| **Migrations vs. catalogue** | 93 Alembic migrations exist; several add entities that were prose-only in the data-model catalogue, and several are controlled repair migrations (`0087`/`0088` removing demo `*-SMOKE*` rows). `36_DATABASE_MIGRATION_CATALOGUE.md` needs reconciliation. | MIG-FR-001, MIG-FR-028 |

---

## 5. Frontend gaps (72 pages)

**Domains with no UI at all:**
- Edge / OT device management, industrial protocol drivers, peripheral (scanner/balance/printer) config (Docs 43–47)
- Machine integration / PLC-SCADA evidence mapping
- Disaster recovery / backup / PITR operations (Doc 76)
- SRE / SLO / capacity / observability dashboards (Doc 78)
- Data-ops consistency & reconciliation, read-model rebuild, dbops (Doc 69/70/75)
- Workflow / Temporal operations
- Contract / event registry browser

**Thin or incomplete UI:**
- Genealogy (page exists, shallow), yield reconciliation, packaging/label reconciliation sub-flows
- QC method master, OOS/OOT full lifecycle
- DDCP execution: missing `handoff-decide`, `fill-sub-actions`, `assembly-verify` screens; batch-readiness view missing a query param
- Batch execution: step material/equipment linkage (blocked on SG-045)

**Known follow-ups already logged (from prior sessions):**
- Page-by-page UX audit not finished; `userSelect` retrofit; `SignedForm` dedup; evidence legal-hold SPEC_GAP
- Several actions found unguarded or Admin-only during the DDCP demo that need proper role splits
- RBAC: 86 permission codes required `scripts/sync_permissions.py` to become reachable; signature-policy catalogues are duplicated between `scripts/seed.py` and `tests/conftest.py`

---

## 6. Test & validation status

| | |
|---|---|
| Backend pytest tests present | **1 159** |
| Executed this session | **None** — test-DB credentials (`GXP_TEST_DB_APP_PW` / `GXP_TEST_DB_MIGRATOR_PW`) are not in the environment; every attempt fails with `asyncpg InvalidPasswordError`. The `2 504 executed` figure in the status files is prior recorded evidence, not re-confirmed here. |
| Test-case library (9 150) | PASS 2 503 · BLOCKED 2 269 · NOT_STARTED 3 708 · IN_PROGRESS 132 · N/A 537 · FAIL 1 |
| Modules `REVIEWED` / `OQ_EXECUTED` / `QUALIFIED` / `RELEASED` | 0 / 0 / 0 / 0 |
| Contract-conformance gate (`tooling/contracts/validate.py`, `tooling/events/validate.py`) | Present; SG-013 notes 0 violations on the committed slice but the slice is incomplete |

To run the backend suite you need the two Postgres roles (`ebmr_new_gxp_app`, `ebmr_new_migrator`) and their passwords exported as `GXP_TEST_DB_APP_PW` / `GXP_TEST_DB_MIGRATOR_PW`, plus `alembic upgrade head` against `ebmr_new_gxp_test`.

---

## 7. The SPEC_GAP register (SG-001 … SG-181)

- **Closed by the 106–115 addenda:** SG-001…SG-011 (ID collisions, signature/retention/RPO/precision/SoD/risk baselines, entity schemas, glossary).
- **Currently blocking:**
  - **SG-013** — API/event field-level schemas incomplete; hinges on **SG-173**.
  - **SG-138** — 24 of 26 QMS signature policy rows still missing.
  - **SG-143** — rules evaluator ignores frozen precision/rounding/UOM policy.
  - **SG-167** — no Document 106 rows for AI-governance signed functions.
- **Reserved for a project-owner decision (not guessable):** SG-173, SG-149, SG-180 (duplicate stores), SG-175 (combination-product ↔ DDCP linkage), SG-045 (recipe material/equipment requirement schema), SG-134–137 (yield waiver / loss catalogue / eDHR export owner), SG-136 (ERP-mismatch → QA hold), SG-158 (holiday calendar), SG-159 (eMDR/E2B mapping).
- **~120 open D/E/R gaps** are "infrastructure this codebase doesn't have yet" or "no endpoint in the spec's own API list" — they hold their modules in `IN_DEVELOPMENT` and account for the 2 269 BLOCKED test cases.

---

## 8. Recommended remediation order

1. **Reconcile status & traceability with reality.** Backfill `build-status.json` / `TRACEABILITY_MASTER.csv` for WP-10/11/12/13/14 code that already exists. You cannot manage gaps you cannot see. *(1–2 days)*
2. **Resolve SG-173** — pick one authoritative store for product / recipe / batch / batch-step, write the cutover migration. Unblocks the SG-013 event half and most of WP-02. *(project-owner decision + migration)*
3. **Close SG-013** — commit the remaining OpenAPI + AsyncAPI contracts (WP-01/02/07/08 operations, all event types), add `expected_version` to every aggregate mutation (SG-014), turn on the conformance gate in CI.
4. **Complete Document 106 signature coverage** — seed the remaining 24 QMS pairs (SG-138), Doc 06/08 remainder (SG-035), AI rows (SG-167), postmarket/security/validation signers (SG-157/160/161/165/170); enforce `reason_required` (SG-091); add `Disposition` to the meaning catalogue or stop using it (SG-141).
5. **Fix SG-143** — make the rules evaluator apply the unit/precision/rounding policy it releases; ratify the Doc 110 calc-class table (SG-145).
6. **Build WP-00 foundations** — CI/CD release pipeline (Doc 103), SBOM + licence register with the missing dependency justifications (Doc 104, incl. the SOAP/SFTP clients SG-153), coding-standard enforcement matrix (Doc 97), branch protection (Doc 99). Required before any validation claim is credible.
7. **WP-11** — set the numeric baselines (SG-166), then trace/verify the infra code that exists; make the explicit build-or-descope decision on NATS (Doc 73) and Temporal (Doc 74) and record it.
8. **WP-06 edge** — build SPEC-EDGE-002/003/004 (Docs 44/45/46); **WP-07 ERP** — resolve SG-121–126 and the adapter dependency approvals.
9. **Execute WP-12** — run IQ/OQ against the built platform, produce validation evidence; this is the only path to `QUALIFIED` / `RELEASED`.
10. **Record the architecture** — `ADR-0007` (Python/FastAPI), `ADR-0008` (Next.js UI role) + a SPEC_GAP against Document 71; decide the fate of `eBMR-ui/`.
11. **Frontend** — build the missing operational UIs (edge, DR, SRE, workflow, contract registry, genealogy depth), finish the DDCP execution screens, run the RBAC hardening / UX audit pass.

---

## 9. Appendix — how to regenerate this view

```bash
# module + requirement rollup
python ebmr-edhr/tooling/status/rollup.py
cat ebmr-edhr/status/BUILD_STATUS.md

# open gaps
grep -nE '^### SG-' ebmr-edhr/docs/generated/18_SPEC_GAPS.md

# capability coverage
column -s, -t ebmr-edhr/docs/generated/42_CAPABILITY_COVERAGE_MATRIX.csv | less -S

# backend endpoint inventory
grep -rE '@[a-z_]*router\.(get|post|put|patch|delete)\(' services/gxp-api/app --include='*.py' | wc -l

# backend tests (needs test DB creds)
cd services/gxp-api && GXP_TEST_DB_APP_PW=... GXP_TEST_DB_MIGRATOR_PW=... .venv/bin/python -m pytest -q
```
