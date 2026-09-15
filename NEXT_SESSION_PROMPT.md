# Continuation prompt — eBMR/eDHR regulated manufacturing platform

Paste everything below into a fresh Claude Code session in `/home/hepin/mydata/eBMR-new` to continue this
project with full context. This file is also saved at `NEXT_SESSION_PROMPT.md` in the repo root if you
need to re-open it later.

---

## 1. What this project is

A U.S.-market regulated eBMR/eDHR (electronic Batch Manufacturing Record / electronic Device History
Record) manufacturing platform, built from a controlled specification baseline (`specs/`, 115 numbered
documents). This is Part 11 / GxP regulated software: electronic signatures, audit trails, mutation
gateways, segregation of duties — treat correctness and evidence-honesty as load-bearing, not optional.

**`CLAUDE.md` at the repo root is the binding project contract — read it in full before doing anything.**
Detailed per-area rules live in `.claude/rules/*.md` (mutation path, signatures, audit/vault, data
ownership, API/event contracts, testing, migrations, dependencies, security, AI governance).

The non-negotiable rules that matter most in practice:
- **`specs/` is read-only.** Never edit it. If a spec is wrong or silent, raise a SPEC_GAP, don't guess.
- **AG-01..AG-15** (architecture non-negotiables, `CLAUDE.md` §2) — memorize these, especially: AG-05 (one
  authoritative store per entity), AG-06 (all regulated mutations go through the Mutation Gateway), AG-08
  (audit/vault/evidence is append-only, DB-privilege-enforced), AG-09 (Postgres outbox is authoritative,
  NATS is transport only), AG-10 (Temporal orchestrates, never holds regulatory truth), AG-11
  (cache/search/read models are non-authoritative and rebuildable), AG-15 (no regulated behavior is
  guessed).
- **The regulated mutation path** (`CLAUDE.md` §3): authenticated context → policy (RBAC+qualification+SoD)
  → signature ceremony if required → Mutation Gateway command (schema, expected_version, idempotency,
  reason) → owning domain service → ONE Postgres transaction (domain state + version + audit + outbox) →
  receipt → outbox publisher → NATS → projections/integrations. Anything that writes regulated state
  outside this path is a defect.
- **SPEC_GAP discipline** (`CLAUDE.md` §4): you may make ordinary engineering decisions, but never invent
  anything touching regulated behavior, record authority, signatures, authorization/SoD, audit/retention
  semantics, quality/release decisions, calculation precision, contract compatibility, migration/data-loss
  behavior, security trust boundaries, or AI decision authority. When such a decision is missing: **do not
  guess** — append an entry to `docs/generated/18_SPEC_GAPS.md` (real path:
  `ebmr-edhr/docs/generated/18_SPEC_GAPS.md`, see §3 below) stating affected requirements, risk, options,
  blocking yes/no, and continue only on unaffected work.
- **No fabricated evidence** (`CLAUDE.md` §5): never invent a test run, scan result, coverage number, or
  signature. A failed test is evidence and stays — never delete it, re-run over it, or edit the expected
  result to make it pass.
- **Before calling any task complete** (`CLAUDE.md` §6), report: requirement IDs implemented; functions
  created/changed; files changed; DB migrations; API/event contract changes; dependency/license changes;
  security impact; test cases executed (PASS/FAIL/BLOCKED counts + every failure's id); validation/change
  impact; traceability/status files updated (include the `rollup.py` summary line); unresolved SPEC_GAPs;
  known limitations.

## 2. Architecture reality vs. the original spec baseline — read this before assuming anything

The original `specs/` baseline assumed a Frappe Framework UI/config layer with ERPNext as an optional
integration target (AG-01), with MariaDB projections. **That is not what actually got built.** Per prior
sessions' own architecture decisions (see `docs/adr/` — ADR-0008 through ADR-0013):

- **`frontend/` (Next.js) is the operator UI of record** (ADR-0010, supersedes the earlier ADR-0008
  Frappe-UI plan), reading the GxP API directly — not the Frappe/MariaDB projection architecture Document
  71 describes (that gap is tracked as **SG-182**, open).
- The **proprietary GxP Core** (`services/gxp-api/`, Python/FastAPI/SQLAlchemy/PostgreSQL) is the one real
  shared codebase — this is where almost all backend work happens, regardless of which spec document or
  work package you're implementing.
- **PostgreSQL is authoritative** (AG-03) for all regulated GxP state (auth: `iam` schema; mutation:
  `mutation` schema — outbox lives here as `mutation.outbox_events`; audit: `audit`; signature:
  `signature`; vault: `vault`; plus one schema per domain module: `ebmr`, `materials`, `qc`, `qms`, `erp`,
  `equipment`, `edge`, `readmodels`, `eventbus`, etc.).
- **NATS/JetStream and Temporal are now real**, not stand-ins — see §4 (WP-11) below. This was the biggest
  "spec says X, actual build was a stand-in" gap and it has been substantially closed this session.
- Real dependencies actually run under PM2 on this host, not Docker-compose-per-service: `ebmr-new-api`
  (uvicorn, port 8010), `ebmr-new-frontend` (Next.js dev, port 4101), `ebmr-new-temporal` (Temporal
  dev-server, headless, embedded SQLite, `127.0.0.1:7233`). NATS JetStream runs in a Docker container
  (`ebmr-new-nats`, `127.0.0.1:4222`, config at `infra/nats-server.conf`). Check `su -s /bin/bash frappe -c
  "pm2 list"` for current process state; `infra/README.md` has the Temporal/NATS setup details.

## 3. The doc tree — this trips people up, read carefully

`/home/hepin/mydata/eBMR-new` contains **two parallel doc-tree structures** (`specs/`, `docs/generated/`,
`test-cases/`, `traceability/`, `status/`, `work-packages/`, `prompts/`):

- **`ebmr-edhr/` is the current, authoritative tree.** All deliverable updates (SPEC_GAPS, test-case
  books, `TEST_CASE_LIBRARY.csv`, `TRACEABILITY_MASTER.csv`, `build-status.json`, `tooling/status/
  rollup.py`, `tooling/guardrails/validate.py`, `tooling/contracts/validate.py`, `tooling/events/
  validate.py`) go here: `ebmr-edhr/docs/generated/18_SPEC_GAPS.md`, `ebmr-edhr/test-cases/...`, etc.
  **It is now git-tracked** (confirmed this session — an earlier memory said it was untracked; that was
  correct at the time but is now stale, it got committed to the repo at some point before this session).
- There is also an older, stale `ebmr-edhr-construction-package-v1.3/`-style copy floating around in some
  historical references — ignore it, it is not where you work.
- The **real, shared codebase** is `services/gxp-api/` at the repo root — same code regardless of which
  doc tree entry you're implementing against. `frontend/` is the Next.js operator UI. `contracts/` (repo
  root, git-tracked) holds the committed OpenAPI/AsyncAPI/JSON-Schema contracts `tooling/contracts/
  validate.py` and `tooling/events/validate.py` check against — note the tooling scripts themselves live
  under `ebmr-edhr/tooling/`, but resolve `REPO_ROOT` up to the actual repo root and check `contracts/`
  there, not inside `ebmr-edhr/`.
- **Before writing a SPEC_GAP claiming "module X doesn't exist,"** grep `services/gxp-api/app/modules/`
  and check `ebmr-edhr/status/build-status.json` first — this codebase has far more built than a quick
  skim suggests (97 of 103 modules started, 15 CODE_COMPLETE). A wrong "doesn't exist" claim has already
  been made and corrected once (SG-132's history), and this session found another instance of the same
  pattern (SG-098's ERP-posting text claimed "no ERP integration exists" when `app/modules/erp/` in fact
  had ~3,300 lines of real, tested adapter code — the text just predated WP-07 landing and was never
  updated). **Docs drift behind the code. Verify against the repo, not the prose.**

## 4. Current build status (as of 2026-09-14)

From `ebmr-edhr/status/build-status.json` / `BUILD_STATUS.md` (regenerate with `python tooling/status/
rollup.py` from inside `ebmr-edhr/`, using the `services/gxp-api/.venv` Python — never hand-edit
`BUILD_STATUS.md`, it's derived):

- **97/103 modules started, 0 released** (stage gate: `REVIEWED`/`OQ_EXECUTED`/`QUALIFIED`/`RELEASED` are
  human-only stages — you may set stages up to `CODE_COMPLETE`).
- 15 modules `CODE_COMPLETE`, 82 `IN_DEVELOPMENT`, 6 `NOT_STARTED`: `SPEC-EDGE-002/003/004` (WP-06 device
  connectivity/store-forward/peripheral — genuinely unstarted), `SPEC-DATA-003` (WP-11 Frappe/MariaDB
  projection architecture — superseded by ADR-0010, see SG-182), `SPEC-ENG-002`/`SPEC-ENG-006` (WP-00
  architecture-rules/testing-strategy meta-documents, not application code).
- **770/2965 requirements verified**, **2533/9150 test cases executed** (of the 9,150 pre-written cases in
  `test-cases/`).
- Current Alembic head: `c3f7a9d2b6e4` (migration `0103_erp_instance_service_actor`), 103 migrations total.
- `main` branch is current; last 6 commits (newest first): PR #23 merge (Stage 5 restart/recovery), Stage
  5 commit, PR #22 merge (SG-067→SG-070 citation fix), citation-fix commit, PR #21 merge (Stage 4 ERP
  consumer), Stage 4 commit.

## 5. What just happened this session — WP-11 (Data/Infrastructure/DR/SRE) Stages 1–5

**SG-183** (`docs/adr/ADR-0011-event-transport-and-durable-workflow.md`) committed to building real NATS/
JetStream and Temporal, replacing interim in-process stand-ins. Five stages landed, each on its own branch
→ PR → CI-green → merge (`wp2X-phase4-wp11-stageN-*`, PRs #18–#23; write-ups at `PHASE_4_WP11.md`,
`PHASE_4_WP11_STAGE2.md`, `..._STAGE3.md`, `..._STAGE4.md`, `..._STAGE5.md` at the repo root — **read
these for full narrative detail**, this section is a summary):

- **Stage 1** (NATS producer): real single-node JetStream broker (`infra/nats-server.conf`, container
  `ebmr-new-nats`); `app/modules/eventbus/jetstream.py` owns connect/publish (bounded 5s connect timeout —
  nats-py's own `max_reconnect_attempts=-1` was found to hang the *initial* connect forever, not just
  reconnects — this cost ~300 minutes of hung CI before being found; apply the same bounded-timeout
  discipline to *any* new blocking external call from the start, not after a second incident);
  `outbox.py::publish_outbox_event()` publishes the canonical envelope with `Nats-Msg-Id=event_id` for
  broker-level dedup.
- **Stage 2** (Temporal): real dev-server (PM2 `ebmr-new-temporal`); `app/modules/workflowops/{client,
  activities,workflows,worker,commands,router}.py`; one real workflow, `StepStuckDetectionWorkflow`
  (BAT-FR-018/021 "stuck step" detection only — deliberately narrow, since almost all of SG-048's other 23
  Document-11 Temporal-dependent requirements are entangled with other unbuilt modules).
- **Stage 3** (NATS consumer, projections): `jetstream.py::pull_subscribe()` (durable pull consumer,
  EVT-FR-009) + `consumer.py::run_pull_consumer()`/`_process_one_message()`/`_dead_letter_message()` — the
  first real driver of `consume_event_idempotently()`/`handle_poison_event()` (both existed since before
  this session but had zero callers). First live consumer: `app/modules/readmodels/projector.py`,
  `material_lot` events → the Postgres search index, reusing an existing, already-reviewed field allowlist
  verbatim (no new field-exposure decision). Added an EVT-FR-014/027 ordering guard to
  `index_authoritative_projection()`.
- **Stage 4** (NATS consumer, integrations): `app/modules/erp/consumer.py` — `MaterialConsumed` →
  the pre-existing, already-tested `queue_erp_command(POST_CONSUMPTION)` pipeline (4 real vendor adapters:
  ERPNext/SAP/Oracle Fusion/Dynamics 365 — but **scoped to ERPNext only**, because every adapter forwards
  its payload to the vendor verbatim with zero transformation layer, so no vendor-neutral payload mapping
  exists to reuse for the other 3). Migration `0103` adds `ErpInstance.service_actor_user_id` (mirrors
  `LimsInstance.service_actor_user_id`, an already-established stand-in for a machine-identity model that
  doesn't exist anywhere in this codebase — SG-070) because a background consumer has no human actor to
  attribute `queue_erp_command()`'s audit row to. Closed SG-098's CON-FR-025 required-behaviour bullet.
- **Stage 5** (Temporal restart/recovery): investigated LIMS/Edge as the next integration-consumer
  candidate and found **neither has any outbound-to-external-system machinery at all** — no HTTP adapter/
  provider layer in either module (unlike ERP's 4 real adapters); both are purely reactive/inbound.
  Building one would mean inventing a whole new outbound adapter layer first — set aside. Pivoted to
  BAT-FR-029 (restart/recovery) instead: `tests/test_workflowops_restart_recovery.py` proves the existing
  `StepStuckDetectionWorkflow` survives an app/worker restart (a fresh `Worker` instance resumes a workflow
  a killed one left durably asleep, exactly once, re-reading live state, not stale) — pure verification, no
  new runtime code, since Temporal already provides this by construction.
- **Also this session**: found and fixed a real, propagating citation bug — `lims_instance.py`'s own
  docstring (and several other files) cited "SG-067" for the LIMS machine-identity stand-in; the real gap
  is **SG-070**, SG-067 is an unrelated NCR gap. Fixed everywhere it had spread, including into this
  session's own Stage 4 text before it was caught. **Lesson: verify a cited SG number against
  `18_SPEC_GAPS.md` directly before repeating it, even when it's copied from existing, seemingly
  authoritative code comments.**

**What's still open from this thread:**
- LIMS/Edge integration consumers — need a new outbound adapter layer built first (real scope, not a
  quick wire-up like ERP was).
- SAP/Oracle/Dynamics ERP consumption posting — needs its own verified vendor-neutral (or per-vendor)
  payload mapping.
- Warehouse mapping for the ERPNext consumption payload (`s_warehouse` currently omitted).
- 18 of SG-048's 24 Document-11 Temporal-dependent requirements (4 resolved: #018, #020, #026, #029;
  #012/#013 explicitly deferred, blocked on SG-045's still-open recipe material/equipment requirement
  schema question).
- TEST-FR-010's deterministic replay/time-skip test harness using `temporalio.testing` — every Temporal
  test so far (Stages 2 and 5) ran against the live dev-server directly, not the replay-test environment.
- Cross-service/multi-consumer contract tests (TEST-FR-007) beyond the individual consumers built.

## 6. The full open SPEC_GAP landscape — 150 open/partial entries, 7 hard-blocking

`ebmr-edhr/docs/generated/18_SPEC_GAPS.md` is the single source of truth (~6,000+ lines; git history back
to 2026-08-21). As of this session there are **185 distinct `spec_gap_id` entries**; roughly **150 are
open or only partially resolved**, and **7 are marked `blocking: true`** (these block specific requirement
verification, not the M1 core build — check each entry's own `blocking` comment for exact scope):

**The 7 hard-blocking gaps** (all Document 58–61, postmarket surveillance / regulatory reporting /
security — signature-policy resolution gaps, not engineering gaps):
- **SG-151** — MULTI-FR-015: no manifest/checksum/file-identity/replay rule shape for the SFTP/CSV/XML/EDI
  batch file adapter.
- **SG-153** — MULTI-FR-014/015: no SOAP or SFTP client dependency has Document 104 justification/
  Security-Architecture approval.
- **SG-156** — Document 106 rows 120-122 (Document 58 signal actions) name signer class as "Per policy
  lookup" with no further resolution.
- **SG-157** — no Document 106 signature policy for `reportability_track.decide`/`regulatory_report.approve`.
- **SG-159** — no approved eMDR/E2B transport mapping spec or reachable submission gateway.
- **SG-160** — Document 60 actions with no Document 106 signature resolution, including an unimplementable
  2-signature requirement.
- **SG-161** — Document 61 (SPEC-SEC-001) has two signature-shaped endpoints with no usable Document 106
  resolution.

All 7 need a human policy decision (a Document 106/113 addendum) before any code can close them — they are
not "go build X" tasks, they're "go get an approved signature-policy value" tasks. If postmarket/Document
58-61 work comes up, read these first and don't attempt to resolve any of them by inventing a signer class.

**Full categorized snapshot of the other ~143 open/partial gaps** (id | one-line title — generated by
parsing `18_SPEC_GAPS.md`'s yaml blocks this session; **treat as a starting index, not gospel** — several
entries below show plain "OPEN" in their own yaml `status:` field but have since been narrated as
partially resolved in prose elsewhere in the file without a fresh yaml block, the same drift pattern
SG-048/SG-098 had before this session touched them; grep the id in the file for the real current state
before planning work against it):

```
SG-021  frontend/ (Next.js) retirement/repurposing timing undecided now Frappe is named operator UI (now moot -- ADR-0010 supersedes ADR-0008, frontend IS the UI of record; this gap's premise is stale)
SG-022  iam_qualification (Document 07) has no schema in the source baseline
SG-023  iam_temporary_authorization (Document 07) has no schema in the source baseline
SG-024  External IdP federation (IAM-FR-002/003) has no Keycloak/OIDC infrastructure in this deployment
SG-025  Device identities / service accounts have no non-human actor concept in the Mutation Gateway
SG-026  Document 107 ACTION_INDEPENDENCE dynamic SoD evaluation has no generic engine beyond one hardcoded case
SG-027  Access review reporting (IAM-FR-026) not implemented
SG-028  8 Document 07 Frappe UI surfaces cannot be built -- apps/ebmr_frappe does not exist (moot per ADR-0010)
SG-029  gxp_audit_event has no formal entity/DDL in the data model catalogue despite being the shared audit table
SG-030  AUD-FR-017/018 (integrity checkpoints + verification job) need a checkpoint/manifest entity
SG-031  AUD-FR-021 (audit review annotation record) needs a new entity
SG-032  AUD-FR-023/024 (numeric retention, legal/quality hold) depend on Document 108's retention baseline (SG-005)
SG-033  AUD-FR-027 (failed-action security trail) is cross-cutting, unclear module ownership
SG-034  7 Document 05 Frappe UI surfaces cannot be built (moot per ADR-0010)
SG-036  11 combined Document 06+08 Frappe UI surfaces cannot be built (moot per ADR-0010)
SG-037  VLT-FR-025 (DDCP cross-constituent vault snapshot) depends on WP-08, not started at gap-write time (WP-08 has since landed -- re-check)
SG-038  MUT-FR-011: SignaturePolicy.reason_required stored but no handler reads/enforces it
SG-039  MUT-FR-026: no dedicated privileged/admin data-repair command type
SG-040  Command-trace/signature-history/manifestation-view/certification-evidence reporting endpoints not implemented
SG-041  SIG-FR-003: signature meaning has no DB-level controlled-catalogue constraint
SG-042  SIG-FR-002: no identity-verification-evidence field on User model
SG-043  product_site_admission / product_external_mapping (Document 09) have no DDL-ready schema
SG-044  Repointing Batch/Recipe at gxp_product_version deferred until Document 10 exists (Document 10 has since landed -- re-check)
SG-045  [PARTIALLY RESOLVED] recipe_material_requirement/recipe_equipment_requirement -- ambiguous policy prose, not a column list. Blocks SG-048 #012/#013.
SG-046  16 Document 10 requirements depend on unbuilt modules/infrastructure
SG-047  [PARTIALLY RESOLVED] gxp_step_result/gxp_step_evidence_link/gxp_batch_hold -- step-scoped slice built, full generality open
SG-048  [PARTIALLY RESOLVED 4/24: #018,#020,#026,#029] 24 Document 11 requirements depend on unbuilt modules -- 18 remain fully open, #012/#013 blocked on SG-045
SG-049  device_component_usage/device_test_result/device_defect/device_evidence_inheritance (Doc 12) prose-only
SG-050  21 Document 12 requirements depend on unbuilt modules/infrastructure
SG-051  POST /genealogy/v1/impact-assessments and /exports have no backing entity
SG-052  Document 13's event-driven write path has no real producers; 5 more requirements depend on absent modules
SG-053  qa_review_item/qa_review_comment (Document 14) prose-only
SG-054  16 Document 14 requirements depend on unbuilt modules/infrastructure
SG-055  15 Document 15 requirements depend on unbuilt modules; non-batch scope types unsupported
SG-056  20 Document 16 requirements depend on unbuilt entities/infrastructure; API list itself incomplete
SG-057  [PARTIALLY RESOLVED] Document 18's material-spec-version dependency chain
SG-058  5 Document 18 requirements have no entity, 1 has no API operation
SG-059  DEV-FR-002/022: automatic candidate creation + release-eligibility wiring, no owning module yet
SG-060  [PARTIALLY_RESOLVED] DEV-FR-014/015: Change Control/Training FK half resolved, rest open
SG-061  DEV-FR-016/021/024: planned-deviation pre-approval, recurrence search, export -- no API operation
SG-062  DEV-FR-023: no notification/escalation worker infrastructure exists anywhere
SG-063  CAPA-FR-008: dependency links to unbuilt Change Control/Training/Validation/Software-Release/Equipment refs
SG-064  CAPA-FR-020/022: metrics/dashboard and export have no API operation
SG-065  CAPA-FR-021 conflicts with Document 27's own API table on which actions need a signature
SG-066  [PARTIALLY RESOLVED] 9 Document 23 requirements depend on unbuilt entities/modules
SG-067  NCR-FR-002/010/011/012/014: cross-module integration (automatic source, SCAR link, release gate, CAPA trigger, destruction) not performed -- NOTE: this is the real NCR gap; do not confuse with the corrected LIMS citation, which is SG-070
SG-068  NCR-FR-017/018: trend metrics and export have no API operation
SG-069  NCR-FR-016: reopen has no API operation
SG-070  4 Document 24 (LIMS) requirements depend on unbuilt infra: real machine-identity source auth, Document 25 OOS records, a test simulator
SG-071  CHG-FR-019: rollback has no API operation
SG-072  CHG-FR-022/023: software PR/build/SBOM traceability, master-record back-linkage -- cross-module, not built
SG-073  CHG-FR-015/024: no update/complete-task operation, no export operation
SG-074  7 Document 25 (OOS) gaps: no CAPA/Change link schema, no reopen/dashboard/export, no QA-review/release wiring, no numeric retest limits
SG-075  material_lot's disposition signature policy row doesn't match Document 106 rows 44/45
SG-076  Document 19 RCV-FR-023/024/025 need a material-scoped QC test spec that doesn't exist (SG-057/063 family)
SG-077  Document 19 needs: UOM conversion, edge/equipment integration, warehouse/location master, ERP -- infra not built
SG-078  DOC-FR-011/023/024: uncontrolled-copy marking, search, export -- no API operation
SG-079  DOC-FR-013/014: training assignment wiring, per-user acknowledgment capture -- not performed
SG-080  DOC-FR-022: no historical-document migration path distinct from the normal signed-release flow
SG-081  [PARTIALLY RESOLVED: read+create only] warehouse_location has no full CRUD -- update/delete/rename open
SG-082  Document 20 needs: barcode/scanner, storage-condition monitoring, label reprint, ERP reconciliation -- infra not built
SG-083  FEFO/FIFO deviation-override + material-spec-version-scoped eligibility need entities that don't exist (SG-057 family)
SG-084  Document 20's cycle-count adjustment has no Document 106 signature row; physical-count freeze has no operation
SG-085  Document 20's genealogy wiring and true cross-site inter-site transfer not built
SG-086  TRN-FR-009: qms.qualification_record and iam.qualifications are two stores for the same concept
SG-087  TRN-FR-007: no numeric attempt-limit/retry-backoff policy for assessment attempts
SG-088  TRN-FR-016/010: training/qualification execution gate not wired into any other module's Mutation Gateway calls
SG-089  TRN-FR-013: Document 30's release()/make_effective() don't trigger retraining assignment
SG-090  TRN-FR-019/023: no overdue-escalation worker, no bulk transcript export
SG-091  signature_policies.reason_required enforced by zero command handlers project-wide
SG-092  Document 106 row 47 signs a create operation for the first time in this codebase (precedent question)
SG-093  Document 21 needs: balance/Edge adapter, environment monitoring, potency/assay-rule execution -- infra not built
SG-094  Document 21's target-quantity/tolerance authority and material_requirement entity don't exist
SG-095  DSP-FR-018's conditional independence can't be expressed by the current signature-policy schema
SG-096  Document 21's label printing/reprint, line/booth clearance, genealogy wiring -- not implemented
SG-097  SCAR-FR-011's source-suspension procurement gate only checked within SCAR's own module, doesn't write ebmr.supplier.status
SG-098  [PARTIALLY_RESOLVED 2026-09-14] Document 22: automatic-consumption (open), reconciliation-tolerance (open), batch-completion gate (open), ERP posting (CON-FR-025 required-behaviour half closed this session -- see SS.5 above)
SG-099  RSK-FR-007's risk-level-tiered acceptance-authority escalation matrix undefined anywhere
SG-100  RSK-FR-009/010/014's cross-module automatic risk-review triggering has no owning command to call yet
SG-101  AUDIT-FR-008/012/015/016/017 have no operation/entity in Document 34's API list or data model
SG-102  AUDIT-FR-003's auditor-independence check limited to same-person overlap; no department-ownership model
SG-103  CMP-FR-011/013/014/015/016/017/018/024 have no operation/cross-module wiring in Document 35's API list
SG-104  CMP-FR-022's privacy/minimization requirement -- no field-level encryption/redaction mechanism anywhere
SG-105  FAR-FR-008's ERP/WMS/CRM consignee-scope resolution is caller-supplied JSONB, not a real cross-system query
SG-106  FAR-FR-016/020 have no cross-module wiring/operation in Document 36's API list
SG-107  MET-FR-003..011/015/017's 9 metric-family calculations, drilldown, threshold-rule eval -- not computed internally
SG-108  MET-FR-019's failed-effectiveness escalation, MET-FR-018's cross-module source ref -- flag-only/unenforced
SG-109  Document 38 (equipment) edge/device/CMMS-dependent requirements have no built source to integrate against
SG-111  EQP-FR-015 pre-use eligibility not wired into batch_execution's step-start command
SG-112  EQP-FR-016/026/027 (reservation, location transfer, retirement) have no API operation
SG-113  Document 38 entities the spec names but the frozen data model doesn't declare (equipment class, calibration standard, spare parts) -- captured only
SG-114  [mostly RESOLVED 2026-08-30, some open] Document 39 (cleaning) requirements with no built source/consumer
SG-115  [mostly RESOLVED 2026-08-30, some open] Document 41 (instruments) requirements with no built source/consumer
SG-116  [mostly RESOLVED 2026-08-30, some open] Document 42 (sterilization) requirements with no built source/consumer
SG-117  [mostly RESOLVED 2026-08-30, some open] Document 40 (aseptic) requirements -- personnel qualification still open
SG-121  Zero data entities declared for all 6 WP-07 ERP modules originally; provisional schema authored under ADR-0009 (module is now substantially built, re-check against current state before treating as "no schema")
SG-122  Document 106 has zero signature-policy rows for any SPEC-ERP-00x action
SG-123  No numeric retry/backoff/max-attempt/circuit-breaker threshold declared anywhere (INT-FR-004/005/022)
SG-124  No auto-resolve rule/tolerance declared for reconciliation differences (INT-FR-019)
SG-125  No credentialed ERPNext/SAP/Oracle/Dynamics sandbox reachable -- adapters built for real, tested only against local stubs -- disclosed-caveat pattern used repeatedly since (Stage 4's own ERPNext scoping cites this precedent)
SG-126  [PARTIALLY_RESOLVED] WP-07 build depth: shared op set + mapping/ledger CRUD built+tested; deep per-vendor mapping, SOAP/file/DB adapters, secret-manager integration open
SG-134  YLD-FR-012's "applicable waiver/profile rule" has no waiver/profile-rule concept in the baseline
SG-135  No controlled catalogue for YLD-FR-021's loss reasons/categories
SG-136  Whether an ERP/WMS inventory mismatch should raise a QA hold is undefined
SG-137  YLD-FR-030's final batch-record export has no owning module, format or signature policy
SG-139  Documents 03/04 declare 7 unimplemented API operations; Document 113 §6 doesn't record their exposure boundary
SG-140  3 different error envelopes specified across Document 101 §5/113 §2/implementation; built one omits correlation_id
SG-141  Signature meaning "Disposition" used in production, not in Document 04's SIG-FR-003 catalogue, no approval record
SG-142  Audit action vocabulary unconstrained -- no registry/enum enforces AUD-FR-005's stable event types
SG-144  SimulateRuleRequest doesn't set extra='forbid' -- POST /rules/v1/{id}/simulate silently accepts unknown fields
SG-148  WP-08 Document 54 (DDCP prefilled-syringe) built from zero: 2 schema deviations, no signature rows, no batch<->profile link
SG-150  Documents 55/56/57 (DDCP autoinjector/inhalation/combination): no Document 112 schema, provisional reuse of Doc 54's tables
SG-152  MULTI-FR-016: no real external ERP DB schema exists for a read-only direct-DB-access adapter
SG-154  postmarket_source field-set conflict between Document 58 and Document 112
SG-155  PMS-FR-020: no statistical/business signal-rule formula exists anywhere in the approved baseline
SG-158  No approved federal holiday calendar for WORK_DAY/WORKING_DAY regulatory deadlines
SG-163  Document 62 application-session idle/absolute timeout has no approved numeric baseline
SG-164  Document 64 rate-limit/webhook-replay-window/upload-byte-cap have no approved numeric baseline
SG-165  Document 68 vulnerability-exception approval names an unresolvable signer role
SG-166  WP-11 Documents 72/75/78 upload-size cap, cache/lag/saturation thresholds have no approved numeric baseline
SG-170  Document 106 row 168 names an unresolvable signer class for generateValidationSummaryReport()
SG-174  Cross-module event-name collisions: LineClearanceCompleted, MaterialReconciliationCalculated -- 2 unrelated producers each
SG-175  [PARTIALLY RESOLVED for sterile_profile_id] Product Master combination-product fields <-> DDCP profile records, two unwired halves
SG-177  [RESOLVED create/list] equipment_area update/delete still open
SG-180  [PARTIALLY RESOLVED] gxp_batch_step (generic) and DDCP's own execution records are two unsynchronized progress trackers
SG-181  qa_review_package/complete + release_scope actions -- "every PERFORMER on the batch" half of IND-002/003 has no data source, stays unenforced
SG-182  Document 71 Frappe/MariaDB projection architecture is not the built architecture (Next.js reads the GxP API directly, ADR-0010)
SG-183  [PARTIALLY_RESOLVED] NATS/Temporal -- see §5 above, this session's own main thread
SG-185  material_specification_version/release has no Document 106 signature policy row
SG-186  qc_method_version/release has no Document 106 signature policy row
```

(SG-001 through SG-020, most of SG-081/175/176/177/178/180/181/035/138/167/169/171 and several others not
listed above are already `RESOLVED`/`RESOLVED_APPROVED` — the full resolution narrative for each, including
every partial/superseding update, is only in `18_SPEC_GAPS.md` itself; the giant status-line paragraph near
the top of the file is the most complete running summary and is worth reading in full once.)

## 7. Known gotchas from this session (save yourself the rediscovery time)

- **Test DB credentials**: `pytest` needs `GXP_TEST_DB_APP_PW` and `GXP_TEST_DB_MIGRATOR_PW` env vars set
  to the `ebmr_new_gxp_app`/`ebmr_new_migrator` Postgres role passwords — read the *current* values out of
  `services/gxp-api/.env` (`GXP_DATABASE_URL`/`GXP_MIGRATION_DATABASE_URL`), don't reuse anything from an
  old transcript (both were rotated once already). Example:
  `APP_PW=$(grep -oP '(?<=ebmr_new_gxp_app:)[^@]+' .env); MIG_PW=$(grep -oP '(?<=ebmr_new_migrator:)[^@]+' .env); GXP_TEST_DB_APP_PW="$APP_PW" GXP_TEST_DB_MIGRATOR_PW="$MIG_PW" python -m pytest ...`
- **Never run two pytest sessions against the test DB at once** — the autouse `clean_database` fixture
  truncates tables; a concurrent run destroys the other's fixtures mid-test with teardown-shaped failures
  (`ForeignKeyViolationError`, `KeyError` on a seeded role) that look like real bugs but are contention.
  Full suite is ~642+ tests / ~60+ minutes — run targeted files for a given change, not the whole suite,
  unless you have time and no other session could be touching the same DB.
- **CSV line-ending trap**: `test-cases/TEST_CASE_LIBRARY.csv` uses CRLF natively;
  `traceability/TRACEABILITY_MASTER.csv` uses bare LF. Python's `csv.writer` always writes `\r\n`
  regardless of source convention when you open with `newline=''` — if you edit either file
  programmatically, normalize to bare `\n` after writing, then re-apply CRLF **only** if the original file
  actually had it (check `b'\r\n' in original_bytes` before writing, restore after). Verify with
  `git diff --stat` afterward — a correct single-row edit should show as a ~2-line diff, not thousands.
  This bit this session twice before being caught.
- **`git checkout -b <branch> main` before a prior PR merges** means the new branch doesn't have that
  PR's changes yet — if you're stacking work, either wait for the prior PR to merge first, or expect a
  `git rebase origin/main` with a real conflict later if both branches touched the same lines (this
  happened once this session, resolved cleanly by taking the superset text).
- **A cited SG number in an existing code comment/docstring is not guaranteed correct** — verify it
  against `18_SPEC_GAPS.md` directly before repeating or extending it (see SG-067-vs-SG-070 above).
- **`nats-py`'s `max_reconnect_attempts=-1` hangs the *initial* connect forever**, not just reconnects, if
  no broker is reachable — always wrap any new blocking external connect (NATS, Temporal, future ERP/LIMS
  live calls, anything) in `asyncio.wait_for(..., timeout=N)` from the start.
- **Real-server tests, never mocked, for infra-backed behavior** — every NATS/Temporal test in this
  codebase runs against the live local broker/server and is skipped (not faked) if unreachable. Follow
  this pattern for anything similar; a mock-only proof of broker/crypto/integration semantics is
  explicitly forbidden (TEST-FR-036).
- **`tooling/guardrails/validate.py`, `tooling/contracts/validate.py`, `tooling/events/validate.py`** (run
  from inside `ebmr-edhr/`, using the `services/gxp-api/.venv` Python) — run all three before every
  commit. Contracts currently has 17 known pre-existing `CTRC-FR-001` findings (uncontracted operations in
  DDCP/equipment/aseptic/sterilization/ERP/LIMS) and events has 2 known pre-existing `CTRC-FR-008`
  findings (SG-174's two event-name collisions) — these are baseline, not something you broke; confirm
  your change doesn't add to the count, don't try to fix them incidentally.
- **`alembic check`** after `alembic upgrade head` against `ebmr_new_gxp_test` is the migration/model-drift
  gate — run it after any schema change.
- **`python tooling/status/rollup.py`** regenerates `status/BUILD_STATUS.md` and recomputes each module's
  `requirements_state` from the real `TEST_CASE_LIBRARY.csv` state — run it after any test-case status
  edit, before committing, and re-check (CI recomputes and fails the build if committed state doesn't
  match a fresh `rollup.py` run).

## 8. Recommended next directions (pick one, or propose your own)

None of these has the same low-risk, self-contained shape Stages 3–5 had — expect to do real scoping and
confirm design forks with the user before building, the same discipline used throughout this session
(verify current repo state → identify genuinely open, safely-buildable scope → confirm with the user →
build → real-server tests → contracts → SPEC_GAP update → traceability/build-status update → PR → CI →
merge).

1. **Build a real LIMS outbound adapter layer**, then wire an event-driven consumer the way ERP got one —
   the largest, most build-heavy option; would need its own vendor-neutral-vs-vendor-specific payload
   decision the way ERP did, likely worse since Document 24 doesn't name a specific vendor precedent.
2. **Pick up one of the 7 blocking Document 58-61 signature-policy gaps** (SG-156/157/159/160/161, plus
   SG-151/153 which are dependency-approval gaps, not signature ones) — these need a human policy decision
   first (a Document 106/113 addendum), so the real first step is presenting the options to the user, not
   writing code.
3. **Continue SG-048's Temporal scope** — of the 18 still-open items, most are entangled with other unbuilt
   modules (Material Service, Equipment master, Document 12/17, IAM qualification/SG-022); re-verify
   against current repo state first, since several of the "not built yet" dependencies this session found
   were stale claims (WP-04/WP-06 are further along than some older gap text assumes).
4. **Work down SG-013's event-half remainder or SG-139/140/142's contract-hygiene gaps** — lower-risk,
   engineering-only cleanup (error envelope consistency, audit action vocabulary, uncontracted operation
   exposure) rather than new capability.
5. **A different work package entirely** — WP-06 (Edge, 3 of 3 modules genuinely NOT_STARTED), WP-08 DDCP
   completeness (SG-148/150 provisional schemas), or whatever the user actually needs next; ask.

Don't assume any of the above is exactly right — verify against the current repo and `18_SPEC_GAPS.md`
before committing to a plan, the same way every stage in §5 started with "verify, don't trust the prose."