# Claude Code prompt — REMEDIATION R1 (Phase 1 gate conditions)

**Run this before `prompts/WP-01/04_SPEC-GXP-002.md`.** It closes four findings from the Phase 1 gate
review of `Work-TCL/eBMRV1.1` @ `c50642a`. The kernel passed; these are the conditions on the "go".

**Repository facts this prompt was written against** (verify they still hold before editing):

- Service: `services/gxp-api`, Python + FastAPI + async SQLAlchemy 2.0 + Alembic
- Transaction boundary: `async with session.begin()` in each router, handlers called inside it
- Kernel: `app/mutation/gateway.py` — `check_idempotency`, `write_audit_event`, `write_outbox_event`,
  `record_command_receipt`
- Errors: `app/mutation/errors.py`, `GxPError` base with `.code` / `.status_code`
- Signature: `app/modules/signature/service.py` — `resolve_policy`, `create_challenge`,
  `consume_challenge`, `sign`; model `signature.signature_policies (record_type, action, meaning,
  required_role_id, requires_independent_signer)`
- Call sites: `app/modules/batch/commands.py` (`complete_step` ~L253, `release_batch` ~L446,
  `_verify_reauth_and_consume` ~L487), `app/modules/material/commands.py` (~L243)
- Migrations: `migrations/versions/` — head is `221dc58877f5_0004_materials_privilege_lockdown`
- Tests: `services/gxp-api/tests/`, fixtures in `conftest.py`, 16 tests currently

**Scope discipline:** these four fixes only. Do not add features, do not refactor modules that are not
listed, do not start Document 04.

---

# FIX 1 — Signature policy must fail closed (BLOCKING)

## The defect

`resolve_policy()` returns `None` when no policy row exists, and the caller decides what to do with that.
In `complete_step` the gate is `if recipe_step.requires_signature:` — a boolean on the *recipe*, not the
policy set. Two ways an unsigned commit gets through today:

1. A recipe step authored with `requires_signature = False` on an action the signature policy covers.
2. A policy row that is missing, mistyped, or not yet seeded — `resolve_policy` returns `None`, no
   exception is raised, and the command commits.

Document 106 SIGP-FR-004 requires the opposite: **an unresolved policy on a regulated state change is a
hard stop**, not a permission.

## Required behaviour

```text
resolve_signature_requirement(record_type, action)
  → policy row found     → signature REQUIRED with that meaning / role / independence
  → no row, action is in the regulated action registry → SIGNATURE_POLICY_UNRESOLVED (fail closed)
  → no row, action explicitly registered as "no signature" → proceed, and audit that decision
```

The third branch matters: "this action deliberately needs no signature" must be *data*, not the absence
of data. Absence of data is an error.

## Implementation

**1. New error** in `app/mutation/errors.py`:

```python
class SignaturePolicyUnresolvedError(GxPError):
    """No signature policy resolved for a regulated action. Fail closed — never commit unsigned
    because policy data is missing (Doc 106 SIGP-FR-004)."""
    code = "SIGNATURE_POLICY_UNRESOLVED"
    status_code = 409
```

**2. Extend `signature.signature_policies`** with the columns Document 106 requires. New Alembic
migration `0005_signature_policy_failclosed`:

```python
op.add_column("signature_policies",
    sa.Column("signature_required", sa.Boolean(), nullable=False, server_default=sa.true()),
    schema="signature")
op.add_column("signature_policies",
    sa.Column("signature_count", sa.SmallInteger(), nullable=False, server_default="1"),
    schema="signature")
op.add_column("signature_policies",
    sa.Column("policy_source", sa.String(30), nullable=False, server_default="PLATFORM_FLOOR"),
    schema="signature")
op.add_column("signature_policies",
    sa.Column("reason_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    schema="signature")
op.create_check_constraint(
    "ck_signature_policies_count", "signature_policies",
    "signature_count BETWEEN 1 AND 4", schema="signature")
```

`signature_required = false` is how you express "this action deliberately needs no signature".

**3. Replace the resolver** in `app/modules/signature/service.py`:

```python
async def resolve_signature_requirement(
    session: AsyncSession, *, record_type: str, action: str
) -> SignaturePolicy:
    """Fail-closed resolution (Doc 106 SIGP-FR-004). A regulated action with no policy row is an
    error, never an implicit permission to commit unsigned."""
    result = await session.execute(
        select(SignaturePolicy).where(
            SignaturePolicy.record_type == record_type,
            SignaturePolicy.action == action,
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise SignaturePolicyUnresolvedError(
            "No signature policy is defined for this regulated action",
            record_type=record_type,
            action=action,
        )
    return policy
```

Keep `resolve_policy` only if something non-regulated still calls it; otherwise delete it so nobody
reaches for the fail-open version by habit.

**4. Rewrite the call sites.** In `complete_step`, the recipe boolean stops being the gate:

```python
policy = await signature_service.resolve_signature_requirement(
    session, record_type="batch_step", action="CompleteStep"
)
if policy.signature_required:
    if cmd.challenge_id is None or not cmd.reauth_password:
        raise MissingSignatureError(
            "This action requires a signature",
            required_meaning=policy.meaning,
        )
    signature_id = await _verify_reauth_and_consume(
        session, actor_user_id, cmd.challenge_id, cmd.reauth_password, batch
    )
    if policy.required_role_id is not None:
        await _assert_signer_role(session, actor_user_id, batch.site_id, policy.required_role_id)
```

`recipe_step.requires_signature` may still *raise* the requirement above the platform floor (a customer
tightening it — Document 106 P3). It may never lower it. Encode that explicitly:

```python
signature_required = policy.signature_required or recipe_step.requires_signature
```

Apply the same shape to `release_batch` (`record_type="batch"`, `action="ReleaseBatch"`) and to the
material disposition path in `app/modules/material/commands.py`.

**5. Seed the policy floor.** Extend `scripts/seed.py` with the Document 106 floor rows for every action
already implemented. Minimum set:

| record_type | action | meaning | signature_required | independent |
|---|---|---|---|---|
| `batch` | `ReleaseBatch` | `Released` | true | true |
| `batch` | `RejectBatch` | `Rejected` | true | true |
| `batch` | `SubmitForReview` | `Performed` | false | false |
| `batch` | `ApproveReview` | `Reviewed` | true | true |
| `batch_step` | `CompleteStep` | `Performed` | true | false |
| `batch_step` | `VerifyStep` | `Verified` | true | true |
| `material_lot` | `Disposition` | `Approved` | true | true |
| `material_lot` | `Issue` | `Performed` | false | false |
| `recipe` | `ReleaseRecipe` | `Released` | true | true |

Seeds are idempotent (upsert on `(record_type, action)`), and rows carry
`policy_source = 'PLATFORM_FLOOR'`.

## Tests (add to `tests/test_batch_flow.py`)

```python
async def test_signature_policy_missing_fails_closed(...):
    """Deleting the policy row must block the command, not permit an unsigned commit."""
    await session.execute(text(
        "DELETE FROM signature.signature_policies "
        "WHERE record_type='batch' AND action='ReleaseBatch'"))
    resp = await client.post(f"/batches/{batch_id}/release", json=valid_release_payload)
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "SIGNATURE_POLICY_UNRESOLVED"
    # and nothing committed
    assert (await session.get(Batch, batch_id)).status != "released"
    assert await count_rows(session, "audit.audit_events", command_type="ReleaseBatch") == 0
```

Plus: `test_recipe_flag_cannot_lower_policy_floor` — recipe step says `requires_signature=False`, policy
says required → signature still demanded.

---

# FIX 2 — Decide tenant scoping now (BLOCKING for schema, not for behaviour)

## The finding

`iam.Organization` exists, so tenancy is modelled — but regulated tables carry only `site_id`. Tenant
isolation is therefore *transitive* (`row → site → organization`), enforced by whichever query remembers
to join. Guardrail AG-05 and Doc 66/70 expect row-level tenant scoping that a forgotten join cannot
bypass.

Both answers are legitimate. What is not legitimate is leaving it undecided while the schema grows —
retrofitting a tenant column across 258 entities later is the expensive version of this conversation.

## Option A — single-tenant per deployment (cheapest, defensible)

Write `docs/adr/ADR-0006-tenancy-model.md`: one organization per database, isolation by deployment
boundary, `Organization` retained for identity and reporting. Then add a guard so the decision cannot
silently rot:

```python
# app/core/db.py or a startup check
async def assert_single_organization(session: AsyncSession) -> None:
    count = (await session.execute(select(func.count()).select_from(Organization))).scalar_one()
    if count > 1:
        raise RuntimeError(
            "Single-tenant deployment (ADR-0006) but multiple organizations exist. "
            "Either revert the extra organization or adopt Option B row-level tenancy."
        )
```

Call it at startup. A second organization appearing is then loud rather than a silent isolation failure.

## Option B — row-level tenancy (correct for shared SaaS)

Migration `0005b_add_tenant_scope`: add `tenant_id UUID NOT NULL` to every regulated table, backfilled
from `site → organization`, with a composite index `(tenant_id, id)` and a FK to `iam.organizations`.
Then add row-level security so a missing `WHERE` clause cannot leak:

```sql
ALTER TABLE ebmr.batches ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON ebmr.batches
  USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

and set `app.tenant_id` from the authenticated actor at the start of each request.

**My recommendation:** Option A now with the startup guard, because your current deployment model is
per-customer and Option B's RLS work is real. But write the ADR today — not "later".

## Test either way

`test_cross_organization_access_denied`: actor in org A requests a batch belonging to a site in org B →
denied, and the error body leaks nothing about whether the record exists.

---

# FIX 3 — The two missing negative tests

Grep found nothing for `rollback`, `orphan`, `outage` or `fail.closed` in `tests/`. These are the two
that decide whether the kernel is trustworthy.

## 3a — Rollback leaves no orphan state

```python
async def test_transaction_rollback_leaves_no_orphan_state(session, client, seeded_batch):
    """Failure after the domain write must leave no domain row, audit event, outbox row or receipt."""
    with patch("app.mutation.gateway.record_command_receipt",
               side_effect=RuntimeError("injected failure after domain write")):
        with pytest.raises(RuntimeError):
            async with session.begin():
                await issue_batch(session, cmd, actor_user_id)

    async with SessionLocal() as fresh:
        batch = await fresh.get(Batch, seeded_batch.id)
        assert batch.status == "planned"       # unchanged
        assert batch.version == 1              # not incremented
        assert await count_rows(fresh, "audit.audit_events", aggregate_id=batch.id) == 0
        assert await count_rows(fresh, "mutation.outbox_events", aggregate_id=batch.id) == 0
        assert await count_rows(fresh, "mutation.command_receipts", aggregate_id=batch.id) == 0
```

Read back through a **fresh session** — asserting on the rolled-back session can pass against identity-map
leftovers and prove nothing.

Inject at three points and run the assertions each time: after the domain write, after the audit write,
after the outbox write.

## 3b — Dependency outage fails closed

The platform must refuse rather than degrade when a compliance-critical dependency is unavailable
(MUT-FR-022).

```python
async def test_signature_service_unavailable_fails_closed(client, seeded_batch):
    with patch("app.modules.signature.service.consume_challenge",
               side_effect=OperationalError("connection lost", None, None)):
        resp = await client.post(f"/batches/{seeded_batch.id}/release", json=valid_release_payload)
    assert resp.status_code >= 400
    assert resp.json()["error_code"] in ("DEPENDENCY_UNAVAILABLE", "SYSTEM_FAULT")
    # the critical assertion: no degraded-mode commit
    async with SessionLocal() as fresh:
        assert (await fresh.get(Batch, seeded_batch.id)).status != "released"
        assert await count_rows(fresh, "signature.signatures", record_id=seeded_batch.id) == 0
```

Repeat with `require_role` raising (authorization path unavailable). If either commits, stop and fix
before anything else — this is the failure mode that ends regulated platforms.

Add `DependencyUnavailableError` (`code = "DEPENDENCY_UNAVAILABLE"`, 503) and map infrastructure
exceptions to it in the FastAPI exception handler, so callers get a stable code instead of a 500.

---

# FIX 4 — Record the two architecture changes

Two frozen decisions were changed in implementation. Both are defensible; neither is recorded. An
unrecorded deviation means the validation package will claim an architecture you did not build.

## ADR-0007 — Python/FastAPI supersedes ADR-010

Document 02 §6.1 froze **ADR-010: TypeScript/Node.js LTS for GxP services**. The implementation is
Python 3.12 + FastAPI + async SQLAlchemy. Write `docs/adr/ADR-0007-python-fastapi-gxp-services.md`
covering:

- **Context:** ADR-010 as frozen; what was actually built
- **Decision:** Python/FastAPI for GxP services, superseding ADR-010
- **Rationale:** single language with the Frappe app layer; one team; async SQLAlchemy gives the explicit
  transaction control the Mutation Gateway needs; Alembic covers the Doc 100 migration standard
- **Consequences:** Doc 97 coding standards need Python equivalents (ruff + mypy strict rather than
  eslint + tsc); `packages/data-contracts` codegen targets Pydantic; **`Decimal` discipline replaces the
  TypeScript decimal library** — every regulated quantity is `Numeric`/`Decimal`, never `float`
  (Doc 110 CALC-FR-001), and this needs a lint rule
- **Status:** Accepted, supersedes ADR-010

Then update `docs/generated/33_CODING_STANDARD_COMPLIANCE_MATRIX.md` so the enforcement column names
Python tooling.

## ADR-0008 — Frappe's actual role

The repo has `apps/frappe` (submodule, `version-16`), `frontend/` (Next.js) and `eBMR-ui/`. Document 02
§5 says Frappe is the *primary application framework*; guardrails AG-01/AG-02 and all of Document 71's
projection rules assume the operator UI is Frappe.

Write `docs/adr/ADR-0008-frappe-role-and-ui-layer.md` answering plainly:

1. Is the operator UI Frappe, Next.js, or Frappe for configuration/back-office and Next.js for execution?
2. If Next.js is the regulated operator UI, what is Frappe for — and does Document 71's
   projection/read-model model still apply, or is the Next.js client reading the GxP API directly?
3. What is `eBMR-ui/` — design assets, a prototype, or a third surface? If it is dead, delete it; a
   third UI directory is where drift starts.

**Whichever answer you give, these still hold and must be restated in the ADR:** no regulated write
outside the Mutation Gateway; no direct database access from any UI; projected GxP fields read-only;
Frappe core never edited (the submodule makes this enforceable).

If the operator UI is genuinely Next.js, say so and raise a SPEC_GAP against Document 71 — that document
assumes Frappe read models and would need reworking. Do not quietly keep both stories alive.

---

# ACCEPTANCE CRITERIA

1. `SIGNATURE_POLICY_UNRESOLVED` returned when a policy row is missing; no unsigned commit is reachable.
2. Recipe flags can raise but never lower the policy floor, proven by test.
3. Policy floor seeded for every implemented action; seeds idempotent.
4. Tenancy ADR written; Option A guard or Option B migration implemented; cross-org test passes.
5. Rollback test passes at three injection points, asserted through a fresh session.
6. Dependency-outage tests pass for signature and authorization paths; no degraded-mode commit.
7. ADR-0007 and ADR-0008 written; coding standard matrix updated.
8. Full suite green: 16 existing tests plus roughly 8 new ones.

# SPEC_GAP RULE

Do not guess regulated behaviour. If Document 106's floor conflicts with an implemented action's
semantics, or if the Frappe/Next.js decision contradicts Document 71, append to
`docs/generated/18_SPEC_GAPS.md` rather than choosing silently.

# COMPLETION REPORT

Requirements addressed; files changed; migrations added (with rollback tested); tests added and **actual**
pass/fail output; the tenancy option chosen and why; the two ADRs; any new SPEC_GAP; known limitations.
