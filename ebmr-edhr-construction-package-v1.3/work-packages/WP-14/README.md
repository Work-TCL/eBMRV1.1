# WP-14 — Customer Deployment / PQ / Go-Live

**Scope:** PQ/UAT, data migration/cutover/reconciliation validation, VSR and validated release authorization.
**Source documents:** 85, 87, 95
**Depends on:** WP-12
**Requirements:** 66 | **Entities:** 7 | **APIs:** 13 | **Events:** 14
**Higher-process-risk modules:** 3 of 3

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

Per-document prompts: `prompts/WP-14/`.
