# tooling/guardrails

Runnable lint for five rows of [`docs/generated/34_ARCHITECTURE_GUARDRAIL_MATRIX.md`](../../docs/generated/34_ARCHITECTURE_GUARDRAIL_MATRIX.md),
matching the four CLAUDE.md §9 hard prohibitions named explicitly in the Phase 2 backbone ratchet
(`PHASE_2_BACKBONE.md` §4 item 6) plus the optional item 5 (float-in-regulated-code lint rule):

| check | guardrail_id | CLAUDE.md §9 line |
|---|---|---|
| `no-cross-module-write` | AG-05 / AG-06 | *(implied by "one authoritative owner/store per regulated entity")* |
| `no-set-value-equivalent` | AG-06 | "No `frappe.db.set_value()` (or equivalent) on regulated data." |
| `no-generic-crud-endpoint` | AG-06 | "No generic CRUD or `PATCH /regulated-record/{id}` style endpoint." |
| `no-bus-publish-without-outbox` | AG-09 | "No publishing to the bus without a committed outbox row." |
| `no-float-for-decimal-column` | AG-04 | "No binary float for a regulated quantity." |

## Run it

```bash
python3 tooling/guardrails/validate.py            # human-readable
python3 tooling/guardrails/validate.py --json      # machine-readable
```

Stdlib-only (`ast` / `pathlib` / `json`) — no `uv sync` needed. Scans `services/gxp-api/app/` only;
`scripts/` (dev/seed tooling, not the regulated runtime path) and `tests/` are out of scope by design,
same as the scope note in `tooling/events/validate.py`.

Exit code 0 clean, 1 on any finding. Wired into the `guardrails` job in `.github/workflows/ci.yml` as a
**blocking** step (not a ratchet — the checked codebase is clean today; a new violation fails the build).

## What each check actually catches

Full rationale for each check, plus the three documented exemptions (one canonical raw-SQL optimistic-
concurrency helper, and the eventbus module's own two outbox-publisher files) is in the module docstring
of `validate.py` itself — read that before changing a check or its allowlist.

Each check is deliberately narrower than the plain-English guardrail row it enforces, because these are
syntax-level AST checks, not a type/data-flow analysis, and the codebase's legitimate patterns had to be
walked first to find where the real line is:

- `no-cross-module-write` does **not** flag reading another module's model (156 legitimate cross-module
  reads exist in `app/modules/` today — joins, existence checks, FK validation). It flags constructing
  and `session.add()`-ing another module's model instance, or a `sqlalchemy.update()`/`delete()` Core
  statement against one.
- `no-set-value-equivalent` does **not** flag every dynamic `setattr()` — a handful of legitimate ones
  pick from a small closed vocabulary based on internal control flow (e.g. choosing between two named
  timestamp fields). It flags `setattr()` whose field name comes from looping over a dict's
  `.items()`/`.keys()` — the actual "copy every provided field onto the record" shape.
- `no-generic-crud-endpoint` does **not** flag PUT/PATCH/DELETE verbs on a resource ID by themselves —
  this codebase already has 8 such routes (material/product/recipe/`*_master`), all legitimate because
  each takes a typed `*Command` parameter through the Mutation Gateway. It flags a PUT/PATCH/DELETE route
  with no typed Command parameter at all.
- `no-bus-publish-without-outbox` allows exactly three files to call `publish_outbox_event` directly (the
  publisher's own two files plus its caller in `app/main.py`); every other call site is a finding.
- `no-float-for-decimal-column` does **not** flag `float` fields in general — engineering timing/duration
  floats (`retry_after_seconds`, `timeout_seconds`, etc.) are pervasive and legitimate throughout
  `app/modules/erp/reliability.py` and similar files. It flags only the one unambiguous, zero-false-
  positive shape: an ORM column whose database type is `Numeric`/`DECIMAL` but whose `Mapped[...]`
  annotation says `float` instead of `Decimal` — a self-contradictory declaration that found one real bug
  (`qms.NcrDisposition.quantity`, fixed alongside this check).

## Tests

`tests/test_guardrails.py` runs each check against a small synthetic `app/modules/` fixture tree under
`tests/fixtures/<check>/` containing one deliberate violation *and* an adjacent allowed pattern, so a
check that flagged indiscriminately fails the "allowed pattern wasn't flagged" assertion just as loudly
as one that flagged nothing. It also asserts the real `services/gxp-api/app/` tree is clean.

```bash
cd services/gxp-api && .venv/bin/python -m pytest ../../ebmr-edhr/tooling/guardrails/tests -v
```

## Extending

Adding a fifth check: add a `check_*` function with the same `(findings, files, modules_root, app_root)`
signature, register it in `CHECKS`, add a fixture pair (violation + allowed) under `tests/fixtures/`, and
a corresponding `test_*` pair in `tests/test_guardrails.py`. If the real codebase has a legitimate
exception, add it to a documented allowlist (see `RAW_SQL_ALLOWLIST_RELPATHS` /
`OUTBOX_PUBLISHER_ALLOWLIST_RELPATHS` for the pattern) rather than weakening the check's pattern-matching
— an allowlist entry is visible in a diff and requires a reason; a loosened pattern silently stops
catching the next real instance too.
