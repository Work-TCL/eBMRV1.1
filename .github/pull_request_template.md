## Work package / requirement

- Work package:
- Requirement IDs implemented:
- Source documents:

## Completion report (mandatory — CLAUDE.md §6)

1. Requirements implemented:
2. Functions created/changed:
3. Files changed:
4. Database migrations (with rollback + `36_DATABASE_MIGRATION_CATALOGUE.md` entry):
5. API/event contract changes (committed to `contracts/` before code):
6. Dependency/licence changes (`40_SBOM_LICENSE_DEPENDENCY_REGISTER.md` + Document 104 justification):
7. Security impact:
8. Tests actually run + real PASS/FAIL/BLOCKED counts + every failure id:
9. Validation/change impact:
10. Traceability + status files updated (include the `rollup.py` summary line):
11. Unresolved SPEC_GAPs:
12. Known limitations:

## Gates (CI: `.github/workflows/ci.yml` — see `39_CI_CD_RELEASE_EVIDENCE_MODEL.md`)

- [ ] No `specs/` edits
- [ ] `ruff check --select F` clean (pyflakes floor)
- [ ] Contract + event conformance gates pass (`tooling/contracts/validate.py`, `tooling/events/validate.py`)
- [ ] Contracts committed before implementation
- [ ] Migration has rollback and a `36_` catalogue entry; `alembic check` clean after `upgrade head`
- [ ] Negative / failure tests for higher-risk functions
- [ ] `rollup.py` run; `BUILD_STATUS.md` and traceability matrices updated
- [ ] SBOM / licence gate green (no PROHIBITED, no UNKNOWN)
- [ ] No fabricated evidence
