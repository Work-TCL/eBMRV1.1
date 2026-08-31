# START HERE — Phase 1 Execution Guide

**Package:** eBMR / eDHR Claude Code Construction Package v1.1
**Read this before running anything.** It tells you exactly how to start Phase 1, what to inspect,
what "good" looks like, what to do next when it is good, and what to do when it is not.

---

# 0. What Phase 1 is

Phase 1 is **not** "build the platform". Phase 1 proves that the construction package is executable and
that the regulated kernel works. It covers:

| Step | What runs | Why it is in Phase 1 |
|---|---|---|
| 0 | Set-up (human) | The agent cannot verify a baseline that is not there |
| 1 | `prompts/00_BOOTSTRAP_PHASE0.md` | Independent verification of the compiled artefacts before any code |
| 2 | `prompts/01_REPOSITORY_FOUNDATION.md` | Skeleton, guardrails, contract tooling, CI gates |
| 3 | `work-packages/WP-00/CLAUDE_CODE_PROMPT.md` | Engineering standards made executable |
| 4 | `prompts/WP-01/03_SPEC-GXP-001.md` | **The pilot module** — the Mutation Gateway |
| 5 | Phase 1 gate review (human) | Go / no-go for the remaining 104 modules |

**Phase 1 succeeds when one regulated command commits through the Mutation Gateway with its audit event
and outbox row in the same transaction, and every negative test observes it refusing.** Nothing else in
the platform matters until that is true.

Document 03 is the pilot deliberately: it is HIGHER-PROCESS-RISK, it carries 32 requirements and 135 test
cases, and every one of the other 104 modules depends on it. If the package can drive Document 03
cleanly, the same prompts will drive the rest. If it cannot, you have found that out after one module
instead of after twelve.

**Rough effort:** Steps 0–3 typically land in the first week; step 4 (the pilot) in the second. Treat
these as planning estimates, not commitments — your team's familiarity with Frappe, Temporal and NATS
will move them either way.

---

# 1. Step 0 — Set-up (human, before any prompt)

## Do this

1. Create the repository and copy the package contents into it. `CLAUDE.md` must sit in the repository root.
2. Populate `specs/` exactly as `specs/README.md` describes:
   - Documents 01–105 → `specs/Documents_01_105/`
   - Approved Documents 106–115 (from `gap-resolution/addenda/`) → `specs/Documents_106_115/`
   - Master index, Authoring Standard, Construction Instructions → `specs/`
3. Apply the seven patches in `gap-resolution/patches/DOCUMENT_PATCH_LIST.md` through document change
   control (two requirement re-namespaces, four event-ownership notes, one acceptance section for Doc 05).
4. Capture the QMS signature records against Documents 106–115.
5. Copy `.claude/settings.example.json` → `.claude/settings.json`.
6. Assign the five roles named throughout the package: Platform Architect, Validation Lead, Head of
   Quality, Security Officer, Data Architect. Prompts reference them; unassigned roles stall reviews.

## Check before moving on

```bash
ls specs/Documents_01_105 | wc -l          # expect 105
ls specs/Documents_106_115 | wc -l         # expect 10
grep -rl "DRV-FR-" specs/Documents_01_105  # expect ONLY Document 44 (not 91)
grep -rl "DEP-FR-" specs/Documents_01_105  # expect ONLY Document 77 (not 104)
grep -c "Acceptance Gate" specs/Documents_01_105/Document_05_*.md   # expect 1
python tooling/status/rollup.py            # expect: 0 started, 0/2965 verified, 0 executed
```

## If a check fails

| Symptom | Action |
|---|---|
| Fewer than 105 documents | Stop. Do not start. A missing specification means the agent will invent its content. |
| `DRV-FR-` still in Document 91 | Patch P-01 not applied. Apply it, then regenerate the traceability artefacts. |
| `DEP-FR-` still in Document 104 | Patch P-02 not applied. Same remedy. |
| `rollup.py` errors | Python 3.9+ available? Run from the repository root. |

---

# 2. Step 1 — Run `prompts/00_BOOTSTRAP_PHASE0.md`

## How to start

Open the repository in Claude Code and paste, or reference, the whole prompt file. Nothing else in the
session. **No coding happens in this step** — that is the point.

## What to check when it finishes

The prompt must produce `docs/generated/PHASE_0_VERIFICATION.md`. Read it against the source, not just
for its conclusion.

### Expected output

1. All 105 + 10 documents accounted for, listed by number.
2. Every Phase-0 artefact in `docs/generated/` reviewed, with a statement per artefact.
3. Conformance checks reported: requirement-ID uniqueness, single event producer, entity ownership,
   operation classes, risk-class coverage.
4. Confirmation that `docs/generated/18_SPEC_GAPS.md` shows **zero open blocking gaps**.
5. An explicit list of anything the agent could not verify.
6. A statement that no production code was written.

### The three things that actually matter

- **Did it find any inconsistency I did not?** I parsed 105 documents mechanically and caught one false
  positive (a *prohibited* endpoint listed as an API). There are probably a few more. A verification
  report that finds two or three real discrepancies is a **good** report.
- **Did it report anything it could not verify?** A report claiming 100% verification of 30 MB of
  artefacts in one pass is not credible — push back on it.
- **Did it stay out of the code?** If `services/` or `apps/` gained files, the agent ignored scope. That
  is a signal about how it will behave in later prompts.

## If the output is as expected

Log the findings, correct any artefact the agent flagged (regenerate rather than hand-edit), then go to
Step 2.

## If the output is not as expected

| Symptom | What it means | Do this |
|---|---|---|
| "Everything verified, no issues" in a short report | It skimmed | Re-run scoped: "verify artefacts 00–10 only, cite specific requirement IDs for each claim" |
| It started writing code | Scope discipline problem | Revert; re-run with the prohibition restated; watch this agent closely in Step 2 |
| It reports a **blocking** gap I closed | Either it is wrong, or Documents 106–115 are not in `specs/` | Check `specs/Documents_106_115/` first; if present, read its argument — it may be right |
| It reports many artefact/spec mismatches (>10) | Extraction quality problem | Do not proceed. Send me the list; the generators are re-runnable |
| It cannot find `specs/` | Set-up incomplete | Return to Step 0 |

**Do not proceed to Step 2 with an unresolved discrepancy in the artefacts.** Everything downstream reads
them as truth.

---

# 3. Step 2 — Run `prompts/01_REPOSITORY_FOUNDATION.md`

## How to start

Fresh session. This is the first prompt that writes files.

## Expected output

- Directory skeleton matching `docs/generated/17_REPOSITORY_STRUCTURE.md` exactly.
- TypeScript strict config; Python typing for the Frappe app.
- `tooling/guardrails/` checks that fail the build on: `specs/` edits, Frappe core edits,
  `frappe.db.set_value` on regulated data, cross-module repository imports, bus publish outside the
  outbox publisher, binary float in a regulated numeric path, raw SQL string building.
- Contract lint + compatibility check + codegen into `packages/data-contracts`.
- Conformance and traceability check jobs.
- CI pipeline wired to all gates.
- **No domain logic.**

## What to check — the only test that counts

The prompt asks for a negative test per guardrail. Verify it yourself, do not take the report's word:

```bash
# Write a deliberate violation and confirm CI rejects it
echo "const qty: number = 1.5;" >> services/gxp-api/src/modules/mutation/scratch.ts
npm run guardrails            # MUST fail on the float rule

git -C specs commit --allow-empty -m "test"   # or touch a spec file
npm run guardrails            # MUST fail on the specs-are-read-only rule
```

Then delete the scratch file. **A guardrail that has never been observed failing is not a guardrail.**

Also check:

```bash
npm run contracts:check       # exists and runs
npm run specs:conformance     # requirement-ID uniqueness + single event producer
npm run traceability:check    # requirement ↔ test mapping
npm run migrations:check      # migration safety
find services apps -name "*.ts" -o -name "*.py" | wc -l   # low — no domain logic yet
```

## If the output is as expected

Commit it as the foundation baseline and tag it. Everything after this is built on top; you want a clean
point to return to. Set WP-00 modules to `CONTRACTS_DRAFTED` where applicable and run the rollup.

## If the output is not as expected

| Symptom | Do this |
|---|---|
| A guardrail does not fail on a deliberate violation | Send it back with the exact violation you wrote and the expected failure. Do not accept "the rule is configured" — demand the failing run |
| Skeleton differs from artefact 17 | Ask which is right and why. If the agent found a genuine conflict, record an ADR; if it drifted, correct it now — 104 modules will inherit the layout |
| Domain logic appeared | Revert those files. It is a scope signal; tighten later prompts to one document at a time |
| Dependencies added without justification | Reject. Document 104 requires: why needed, whether an approved dependency solves it, package/version/source/hash, licence, security/EOL, SBOM effect, alternatives, approval |
| CI is green but no job actually ran | Check the job logs, not the badge. Fabricated evidence is the failure mode to watch for all the way through |

---

# 4. Step 3 — Run `work-packages/WP-00/CLAUDE_CODE_PROMPT.md`

## Expected output

The engineering standards from Documents 97–104 become executable: lint rules, type rules, migration
tooling, contract tooling, test harness, CI evidence model, SBOM generation, branch protection config.
Still no domain logic.

## What to check

- Each of Documents 97–104 has its requirements reflected in a real check, not a document restating them.
- `docs/generated/33_CODING_STANDARD_COMPLIANCE_MATRIX.md` rows map to actual tooling that runs.
- SBOM generation produces a real file with real packages (the register I shipped is deliberately empty —
  this is where it gets populated).
- Test harness can run the mandatory module suite shape (14 cases) even with no module implemented.

## If good → Step 4. If not

Same pattern as Step 2: demand the failing run, not the configuration. WP-00 is where evidence discipline
gets established; if it is loose here it stays loose.

---

# 5. Step 4 — The pilot: `prompts/WP-01/03_SPEC-GXP-001.md`

This is the real test of the whole package.

## How to start

Fresh session, one document only. Do **not** run the whole WP-01 prompt yet — Documents 04–08 come after
the pilot passes.

## Expected output

| Deliverable | Where | Expected |
|---|---|---|
| Contracts | `contracts/openapi/spec-gxp-001.yaml` | `POST /gxp/v1/commands/{commandType}` with canonical command envelope, MutationReceipt, error schema; `additionalProperties: false`; `x-requirement-ids` |
| Schema | `services/gxp-api/src/modules/mutation/migrations/` | `gxp_command_receipt`, `gxp_outbox`, idempotency store — with tenant scope, version, retention class, rollback |
| Code | `services/gxp-api/src/modules/mutation/` | The command handler in the exact shape in `.claude/rules/01-gxp-mutation-rules.md` |
| Tests | module test dir | The 135 cases from `test-cases/WP-01/Document_03_SPEC-GXP-001_TEST_CASES.md` |
| Results | `test-cases/TEST_CASE_LIBRARY.csv` | 135 rows with status, executor, timestamp, actual result |
| Evidence | `validation/evidence/oq/SPEC-GXP-001/` | Per case: request/response, state proof, audit id, outbox row |
| Traceability | `traceability/TRACEABILITY_MASTER.csv` | 32 rows updated: build_stage, verification_state, test_case_ids, evidence_location |
| Status | `status/build-status.json` | Module stage set; `requirements_state` per MUT-FR |

## The seven checks that decide go / no-go

Run these yourself. They are the difference between "it compiled" and "the kernel works".

**1. One transaction, four writes.** Commit one regulated command. Then:

```sql
SELECT * FROM gxp_command_receipt WHERE command_id = '<id>';
SELECT * FROM gxp_audit_event     WHERE command_id = '<id>';
SELECT * FROM gxp_outbox          WHERE command_id = '<id>';
```
Domain row, version increment, exactly one audit event, exactly one outbox row. All present or all absent —
never three of four.

**2. Rollback leaves nothing.** Inject a failure after the domain write, before commit. Re-run the three
queries: zero rows everywhere. (`TC-003-M13`)

**3. Stale version is refused.** Read version N, let another actor commit, submit with `expected_version =
N`. Expect `STALE_VERSION`, no partial write. (`TC-003-M08`)

**4. Duplicate key returns the original.** Same command twice, same idempotency key: second call returns
the first receipt, and there is still exactly one audit event and one outbox row. (`TC-003-M09`)
Then same key with a changed payload → `IDEMPOTENCY_CONFLICT`. (`TC-003-M10`)

**5. Dependency outage fails closed.** Stop the policy service. Invoke a regulated command. Expect
`DEPENDENCY_UNAVAILABLE` and **no commit**. If it commits in a degraded mode, stop the project and fix it
— this is the single most dangerous failure mode in the platform. (`TC-003-M12`)

**6. No bypass path exists.** MUT-FR-001 requires it architecturally, not by convention:

```bash
npm run guardrails
grep -rn "frappe.db.set_value\|UPDATE gxp_" services apps | grep -v test   # expect nothing
```

**7. The evidence is real.** Open three test cases at random from the CSV and check the evidence folder
actually contains what the case named. Then re-run those three yourself. If any result cannot be
reproduced, treat every result in the run as unverified.

## If the pilot passes

1. Have the Platform Architect review the code against `.claude/rules/01-gxp-mutation-rules.md` and set
   the module to `REVIEWED` in `build-status.json`.
2. Run `python tooling/status/rollup.py` — expect 1/103 modules started, 32/2965 requirements verified,
   135 cases executed.
3. Tag the repository. This is your kernel baseline.
4. **Then, and only then, continue in this order:**
   - `prompts/WP-01/04_SPEC-GXP-002.md` (signature) — depends on the Document 106 policy set
   - `prompts/WP-01/05_SPEC-GXP-003.md` (audit)
   - `prompts/WP-01/06_SPEC-GXP-004.md` (vault)
   - `prompts/WP-01/07_SPEC-IAM-001.md` (identity/policy/SoD — with Document 107 rules)
   - `prompts/WP-01/08_SPEC-GXP-006.md` (rules & calculation — with Document 110 precision policy)
5. Start **WP-10 (security), WP-11 (data/infrastructure) and WP-12 (validation) in parallel** from here.
   They are numbered as packages so they have owners, not so they can be deferred. Deferring them is the
   most common way regulated platforms become unvalidatable.
6. Review the pilot's completion report for prompt-quality feedback: which sections did the agent have to
   guess at? Those sections need strengthening before the same weakness repeats across 104 modules.

## If the pilot does not pass

Diagnose by symptom — the remedy differs sharply:

| Symptom | Root cause | Remedy |
|---|---|---|
| Commits without an audit event or outbox row | Transaction boundary wrong | Reject. Point at the code pattern in `.claude/rules/01-gxp-mutation-rules.md`; require checks 1 and 2 to pass before anything else |
| Degraded-mode commit when a dependency is down | Fail-open design | Reject immediately. This is MUT-FR-022 and it is not negotiable |
| Idempotency implemented in the UI only | Misread the requirement | Re-run with MUT-FR-010/025 quoted; integration callers retry too |
| Tests written by the agent instead of the supplied book | It ignored the test section | Discard its tests. Re-run pointing only at the test case book; the books are the acceptance criteria |
| Test results recorded but evidence folders empty | Evidence discipline missing | Treat all results as unexecuted. Re-run with evidence capture as the first requirement |
| Results claimed but not reproducible | Fabricated evidence | Stop. Discard the run entirely, restart from the tagged foundation baseline, and add a human witness for the re-run |
| Prompt too large to complete in one session | Granularity | Split by section: contracts → schema → handler → tests. The prompt is designed to survive being split |
| Agent raises a SPEC_GAP | Possibly correct | Read it properly. Document 03 is the most precisely specified document in the baseline, so a genuine gap here is significant — send it to me and I will assess it against the source |
| Code works but violates a guardrail | Convention over architecture | Reject. A bypass that works today is a bypass that ships |

**The stop rule:** if two consecutive attempts at Document 03 fail checks 1, 2 or 5, do not push on to
Document 04. The problem is the prompt or the model's grasp of the transaction pattern, and every
downstream module will inherit it. Come back with the failing output and we fix the prompt.

---

# 6. Step 5 — Phase 1 gate review (human)

Convene the Platform Architect, Validation Lead and Head of Quality. Five questions:

1. Did the guardrails demonstrably reject violations? (Not "are they configured")
2. Did the Mutation Gateway pass all seven checks, including the fail-closed case?
3. Was every one of the 135 test cases executed with reproducible evidence?
4. Are traceability and status accurate — do they match what actually exists on disk?
5. What did the pilot reveal about prompt quality that needs fixing before 104 more modules?

**Go:** proceed through WP-01, and start WP-10/11/12 in parallel.
**No-go:** fix the specific failure above; do not proceed on parallel tracks to "make progress". In a
regulated build, parallel progress on a broken kernel is negative progress — every module built on it
gets rebuilt.

---

# 7. Standing rules for every phase after this

- **One document per session** for HIGHER-PROCESS-RISK modules (102 of 105 are).
- **Read the completion report before starting the next prompt.** It is where fabricated claims, missed
  requirements and drift are cheapest to catch.
- **Check `status/BUILD_STATUS.md` every morning.** It answers "what is built and how far" at three levels.
- **Never let an agent set `REVIEWED`, `OQ_EXECUTED`, `QUALIFIED` or `RELEASED`.** Those are human
  decisions and the package enforces it.
- **A failed test is evidence.** It is never deleted, re-run over, or edited to pass.
- **A new SPEC_GAP stops work on the affected scope only.** Record it, keep moving elsewhere, resolve it
  the way Documents 106–115 were resolved: analysis, options, named approver.
- **Regenerate, do not hand-edit** anything in `docs/generated/`, `traceability/` or `status/`.

---

# 8. The two-line version

> Populate `specs/`, apply the seven patches, then run `prompts/00_BOOTSTRAP_PHASE0.md`.
> Phase 1 is complete when Document 03 commits one regulated command with its audit event and outbox row
> in one transaction, refuses every negative case, and fails closed when a dependency is down — with
> reproducible evidence for all 135 test cases.
