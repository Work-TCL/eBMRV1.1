# Phase 4 — WP-07 remainder: ON_PREM secret-manager provider (SG-126 item 3)

**Date:** 2026-09-12
**Branch:** `wp18-phase4-wp07-secret-manager` (based on `main` at `60546e5`, the merge of PR #14's WP-04
QC method-master work)
**Scope:** the ON_PREM half of SG-126 item (3) — "no secret-manager integration exists anywhere in this
codebase yet" — chosen after the user picked between two legitimate scopes for this branch.

---

## 0. Scoping investigation before building anything

SG-126 item (3) as written implied a secret manager needed to be built from scratch. Direct code
inspection found the picture was more specific than that:

- `app/modules/security/crypto.py::resolve_secret()` (Document 65) already existed and was **deliberately
  authorization/audit-only** — it checks a `secret_metadata` row's `consumer_identities` allowlist and
  `state == "ACTIVE"`, then returns a handle, by design never fetching a value. This is correct Document 65
  behavior (# 14: never a secret value in an ordinary table), not an oversight.
- No **create** path for a `secret_metadata` row existed at all. The only mutation was `rotate_secret()`,
  which requires the row to already exist (`session.get(SecretMetadata, cmd.secret_id)`, `NotFoundError`
  otherwise).
- `app/modules/erp/commands.py::build_adapter()` passes `instance.auth_secret_ref` directly as the
  credential, with its own comment naming this exact gap.

Given two genuinely different, both-legitimate ways to close this (wire `resolve_secret()`'s
authorization check into ERP only vs. also build a real ON_PREM encrypted secret-value store), the choice
was put to the user rather than assumed. The user chose the larger scope: build the ON_PREM store.

## 1. What was built

**`security.secret_value`** (new table, migration `0101_secret_value_schema`, `a4e9c2f6b1d8`) — one row
per ON_PREM secret, holding only an AES-256-GCM envelope (`{algorithm, key_version, key_context, nonce,
ciphertext, aad}`), never plaintext. Reuses the existing `encrypt_sensitive_field`/`decrypt_sensitive_field`
primitives (Document 65, `cryptography`'s AESGCM) — **zero new dependencies**. This is the first real
caller of those functions anywhere in the codebase; every other module that could use field encryption
hasn't yet.

**`create_secret()` / `POST /security/v1/secrets`** — the missing create path for `secret_metadata`.
Validates `provider` against `{K8S_SECRET, AWS_SM, VAULT, ON_PREM}`; `initial_value` accepted only for
`provider=ON_PREM` (encrypted immediately, rejected outright for every other provider since this build has
no client to write a value there). RBAC-only (Security Admin), no Document 106 row — same class as the
pre-existing `secret.rotate`.

**`set_secret_value()` / `POST /security/v1/secrets/{id}/value`** — stores/replaces an ON_PREM secret's
encrypted value under its own optimistic-concurrency `version` (0 means "nothing stored yet"). Rejects
non-ON_PREM providers. RBAC-only, no signature.

**`fetch_secret_value()` in `crypto.py`** — the actual value-fetch function Document 65 always described
as the caller's own responsibility. Calls `resolve_secret()` first (unchanged authorization/audit path),
then for `provider=ON_PREM` decrypts and returns the real value; for K8S_SECRET/AWS_SM/VAULT it **fails
closed** with the new `SECRET_PROVIDER_NOT_INTEGRATED` (501) rather than fabricating a fetch — no live
client for any of those exists in this build, and building one needs both a reachable vendor endpoint to
verify against (none available, same constraint the ERP adapters already live with — SG-125) and a
Document 104 dependency justification for the relevant SDK (`boto3`/`hvac`/`kubernetes`), neither of which
exists yet. Also added `is_registered_secret()`, a query helper.

**ERP wiring** — `app/modules/erp/commands.py::build_adapter()` is now `async` and, when
`instance.auth_secret_ref` names a secret actually registered in `secret_metadata`, resolves it through
`fetch_secret_value()` (service identity `erp_instance:{id}`) instead of using the ref directly. An
unregistered ref — every pre-existing `ErpInstance` row in this codebase and every test that registers one
via the API — falls back to the exact pre-existing behavior. **This is purely additive**: no existing
instance's behavior changes, verified by two new direct tests exercising both branches. Both call sites
(`get_capabilities()`, `dispatch_erp_command()`) and `erp/sync.py`'s pull pipeline were updated to `await`
the now-async function; two existing test monkeypatches (`test_erp_flow.py`, `test_erp_master_sync.py`)
were updated from a plain lambda to an async fake.

## 2. Contract

`contracts/openapi/spec-sec-005.yaml` — 2 new operations (`postCreateSecret`, `postSetSecretValue`) + 2 new
schemas (`CreateSecretCommand`, `SetSecretValueCommand`), module description updated to name the 4th owned
entity and `fetchSecretValue()`. `tooling/contracts/validate.py --baseline` PASS (no new unbaselined
findings). `tooling/guardrails/validate.py` PASS (5/5 checks).

## 3. Updated SPEC_GAP

**SG-126** — item (3) moved from "untouched" to **partially resolved**. ON_PREM provider closed
end-to-end (create → store value → fetch value → consumed by a real caller, ERP). K8S_SECRET/AWS_SM/VAULT
remain open, recorded as still needing a live target plus Document 104 approval — not guessed, not
silently left implied-done.

## 4. Test evidence

- `tests/test_crypto_secrets_pki.py`: grew from 10 to **18 tests**, real run **18/18 passed**. New
  coverage: `create_secret` (registration, duplicate-ref rejection, provider validation, ON_PREM
  initial-value encryption + round-trip fetch, rejecting `initial_value` for non-ON_PREM providers),
  `set_secret_value` (create-then-update with optimistic concurrency, non-ON_PREM rejection),
  `fetch_secret_value` (provider-not-integrated fail-closed, value-not-set fail-closed, consumer-allowlist
  enforcement even with a stored value), `is_registered_secret`, and an RBAC-denial test on the new
  endpoints.
- `tests/test_erp_flow.py` + `tests/test_erp_master_sync.py`: **58/58 passed** (53 + 5), including 2 new
  tests proving `build_adapter()`'s managed-secret and legacy-fallback branches both work, with the
  pre-existing 56 unaffected.
- Full repository test suite re-run kicked off after these changes; final PASS/FAIL/BLOCKED counts and any
  failures will be reported in the completion summary once it finishes (backgrounded, ~60 min baseline).

## 5. Traceability / build-status / test-case updates

- `docs/generated/18_SPEC_GAPS.md` — SG-126 updated (title, description, source_documents/requirement_ids,
  affected_functions, resolution_document, status stays `PARTIALLY_RESOLVED`).
- `docs/generated/04_DATA_MODEL_CATALOGUE.md` — new `secret_value` entity documented under Document 65.
- `docs/generated/05_DATABASE_OWNERSHIP_MATRIX.md` — new `secret_value` row.
- `traceability/TRACEABILITY_MASTER.csv` — TR rows for KEY-FR-002/003/004 updated (entities, api_operations,
  events, gap_reference).
- `test-cases/WP-10/Document_65_SPEC-SEC-005_TEST_CASES.md` + `test-cases/TEST_CASE_LIBRARY.csv` —
  TC-065-002-01/003-01/004-01 moved NOT_STARTED → PASS with real evidence citations.
- `status/build-status.json` — SPEC-SEC-005 (entities/apis/events counts, KEY-FR-002 → VERIFIED, test_pass
  25→28, new stage_history entry) and SPEC-ERP-001 (test_pass +2, new stage_history entry) updated;
  `tooling/status/rollup.py` re-run.
