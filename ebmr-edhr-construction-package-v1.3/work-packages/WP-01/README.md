# WP-01 — GxP Core — Mutation / Signature / Audit / Vault / IAM / Rules

**Scope:** The regulated kernel: every later module depends on these six services.
**Source documents:** 03, 04, 05, 06, 07, 08
**Depends on:** WP-00
**Requirements:** 186 | **Entities:** 18 | **APIs:** 31 | **Events:** 0
**Higher-process-risk modules:** 6 of 6

| File | Contents |
|---|---|
| `01_SCOPE_AND_REQUIREMENTS.md` | every requirement in scope |
| `02_DEPENDENCIES.md` | upstream/downstream and entry conditions |
| `03_FUNCTION_CONTRACTS.md` | function/service contracts |
| `04_DATA_MODEL.md` | entities, ownership, migrations |
| `05_API_EVENT_CONTRACTS.md` | operations and events |
| `06_UI_WORKFLOWS.md` | UI surfaces and action→API mapping |
| `07_SECURITY_AUTH_SIGNATURE.md` | authorization, SoD, signature points |
| `08_IMPLEMENTATION_SEQUENCE.md` | ordered build steps |
| `09_TEST_PLAN.md` | tests by type and risk |
| `10_VALIDATION_IMPACT.md` | qualification and evidence |
| `11_ACCEPTANCE_CHECKLIST.md` | exit gate |
| `12_SPEC_GAPS.md` | gaps affecting this package |
| `CLAUDE_CODE_PROMPT.md` | the prompt to run |

Per-document prompts: `prompts/WP-01/`.
