# Prompt execution order

Run these in order. Each prompt is self-contained; each work-package prompt delegates to its
per-document sub-prompts under `prompts/WP-XX/`.

```text
00. prompts/00_BOOTSTRAP_PHASE0.md        verify baseline and Phase-0 artefacts (no coding)
01. prompts/01_REPOSITORY_FOUNDATION.md   skeleton, guardrails, contracts tooling, CI gates
```

Then, in dependency order:

01. `work-packages/WP-00/CLAUDE_CODE_PROMPT.md` — Repository, Tooling & Contract Foundations
02. `work-packages/WP-01/CLAUDE_CODE_PROMPT.md` — GxP Core — Mutation / Signature / Audit / Vault / IAM / Rules
03. `work-packages/WP-02/CLAUDE_CODE_PROMPT.md` — Product / Recipe / Batch Execution
04. `work-packages/WP-03/CLAUDE_CODE_PROMPT.md` — Genealogy / Review / Release / Packaging / Yield
05. `work-packages/WP-04/CLAUDE_CODE_PROMPT.md` — Procurement / Materials / QC
06. `work-packages/WP-05/CLAUDE_CODE_PROMPT.md` — Quality Management System
07. `work-packages/WP-06/CLAUDE_CODE_PROMPT.md` — Equipment / Sterile / Edge
08. `work-packages/WP-07/CLAUDE_CODE_PROMPT.md` — Enterprise Integrations
09. `work-packages/WP-08/CLAUDE_CODE_PROMPT.md` — DDCP Product Profiles
10. `work-packages/WP-09/CLAUDE_CODE_PROMPT.md` — Postmarket
11. `work-packages/WP-10/CLAUDE_CODE_PROMPT.md` — Security
12. `work-packages/WP-11/CLAUDE_CODE_PROMPT.md` — Data / Infrastructure / DR / SRE
13. `work-packages/WP-12/CLAUDE_CODE_PROMPT.md` — Validation Platform & Evidence
14. `work-packages/WP-13/CLAUDE_CODE_PROMPT.md` — AI Advisory Capabilities
15. `work-packages/WP-14/CLAUDE_CODE_PROMPT.md` — Customer Deployment / PQ / Go-Live

## Sub-prompts

- `prompts/WP-00/` — 10 document-level prompts
- `prompts/WP-01/` — 6 document-level prompts
- `prompts/WP-02/` — 4 document-level prompts
- `prompts/WP-03/` — 5 document-level prompts
- `prompts/WP-04/` — 8 document-level prompts
- `prompts/WP-05/` — 12 document-level prompts
- `prompts/WP-06/` — 10 document-level prompts
- `prompts/WP-07/` — 6 document-level prompts
- `prompts/WP-08/` — 4 document-level prompts
- `prompts/WP-09/` — 3 document-level prompts
- `prompts/WP-10/` — 8 document-level prompts
- `prompts/WP-11/` — 10 document-level prompts
- `prompts/WP-12/` — 15 document-level prompts
- `prompts/WP-13/` — 1 document-level prompts
- `prompts/WP-14/` — 3 document-level prompts

Total: 105 per-document prompts + 15 work-package prompts + 2 top-level prompts.

## Rules for every prompt

- Never edit `specs/`.
- Never guess regulated behaviour — raise a SPEC_GAP.
- Never fabricate evidence.
- Always deliver the twelve-point completion report.
