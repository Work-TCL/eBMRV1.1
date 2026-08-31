# 20 — Product Profile Inheritance Map

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** How DDCP product profiles (Docs 54–57) inherit and constrain the common execution platform.

---

```text
Platform execution core (Docs 09–17)
  ↓ inherits
Product / constituent regulatory profile (Doc 09)
  ↓ inherits
DDCP profile (Docs 54–57)
  ↓ constrains
Master recipe / MMR (Doc 10) → batch execution (Doc 11) → eDHR (Doc 12)
  ↓ feeds
Release/disposition (Doc 15), genealogy (Doc 13), postmarket (Docs 58–60)
```

| Profile | Document | Constituent scope | Profile-specific entities | Requirements |
|---|---|---|---|---|
| Prefilled Syringe & Injectable DDCP Manufacturing Profile | 54 | drug + device constituent | `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`, `fill_operation`, `production_count_ledger`, `device_assembly_record`, `device_functional_test_link`, `ddcp_release_checkpoint`, `batch_evidence_manifest` | PFS-FR-001..030 (30) |
| Autoinjector, Pen Injector & Cartridge-Based DDCP Manufacturing Profile | 55 | drug + device constituent | declared in prose — schema completion required | INJ-FR-001..030 (30) |
| Inhalation DDCP Manufacturing Profile — MDI / DPI | 56 | drug + device constituent | declared in prose — schema completion required | INH-FR-001..030 (30) |
| Drug-Eluting / Drug-Coated Device DDCP Manufacturing Profile | 57 | drug + device constituent | declared in prose — schema completion required | COAT-FR-001..030 (30) |

## Inheritance rules

- A profile may add required steps, evidence, checks and release checkpoints; it may not remove a platform control.
- A profile never duplicates QC, genealogy, equipment or audit tables (Doc 54 §7).
- Profile versions are released, versioned artefacts subject to change control (Doc 29).
- Constituent handoff points are explicit contracts between drug and device execution paths.
- Profile selection is part of the product regulatory profile (Doc 09) and is frozen into the batch snapshot at issue.
