# Prompt 00 — Bootstrap & Phase-0 verification

TASK:
Ingest the controlled baseline and verify the Phase-0 construction package before any coding.

SOURCE OF TRUTH:
1. `specs/MASTER_00_eBMR_eDHR_Document_Index_and_Usage_Guide.md`
2. `specs/Documents_01_105/` (Documents 01–105)
3. `specs/Documents_106_115/` (approved gap-resolution baselines)
4. `specs/Specification_Authoring_Standard_Implementation_Ready_v1_0.md`
5. `specs/ClaudeCode_Master_Project_Construction_Instructions_v1_7_FINAL_Documents_01_105.md`
6. `CLAUDE.md` and `.claude/rules/`

DO NOT start production coding in this prompt.

STEPS:
1. Verify exactly one preferred document exists for each number 01–105 and that 106–115 are present and APPROVED.
2. Confirm the seven patches in `gap-resolution/patches/DOCUMENT_PATCH_LIST.md` have been applied; if not, stop and report.
3. Read every artefact in `docs/generated/` and check it against the specifications you ingested.
4. Report any artefact that is inconsistent with a source document — do not silently correct it.
5. Re-run the conformance checks: requirement-ID uniqueness, single event producer per type,
   every entity has an owner, every operation has a class, every module has a risk class.
6. Confirm `docs/generated/18_SPEC_GAPS.md` shows zero open blocking gaps.
7. Produce `docs/generated/PHASE_0_VERIFICATION.md` stating what you verified, what you could not verify,
   and any new SPEC_GAP you found.

ACCEPTANCE CRITERIA:
- 105 + 10 documents accounted for
- every Phase-0 artefact reviewed
- zero open blocking gaps, or the blockers listed explicitly
- verification report written

COMPLETION REPORT:
documents verified; artefacts reviewed; inconsistencies found; new SPEC_GAPs; confirmation that no
production code was written.
