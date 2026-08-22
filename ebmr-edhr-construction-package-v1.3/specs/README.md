# Controlled specification baseline

Place the controlled documents here exactly as issued. **This directory is read-only to the coding agent.**

```text
specs/
├── MASTER_00_eBMR_eDHR_Document_Index_and_Usage_Guide.md
├── Specification_Authoring_Standard_Implementation_Ready_v1_0.md
├── ClaudeCode_Master_Project_Construction_Instructions_v1_7_FINAL_Documents_01_105.md
├── eBMR_eDHR_Final_Ingestion_Manifest_01_105.json
├── Documents_01_105/
│   ├── Document_01_...FROZEN.md
│   ├── Document_02_....md
│   └── ... through Document_105_....md
└── Documents_106_115/                     # approved gap-resolution baselines
    ├── Document_106_Signature_Policy_Baseline_..._APPROVED.md
    ├── Document_107_Segregation_of_Duties_..._APPROVED.md
    ├── Document_108_Record_Retention_..._APPROVED.md
    ├── Document_109_Availability_RPO_RTO_SLO_..._APPROVED.md
    ├── Document_110_Calculation_Precision_..._APPROVED.md
    ├── Document_111_GxP_Function_Risk_Classification_..._APPROVED.md
    ├── Document_112_Entity_Schema_Completion_..._APPROVED.md
    ├── Document_113_Contract_Completion_Standard_APPROVED.md
    ├── Document_114_Platform_Glossary_..._APPROVED.md
    └── Document_115_ID_Namespace_..._APPROVED.md
```

## Before first use

1. Copy Documents 01–105 from the controlled repository into `Documents_01_105/`.
2. Copy the approved Documents 106–115 from `gap-resolution/addenda/` into `Documents_106_115/`.
3. Apply the seven patches in `gap-resolution/patches/DOCUMENT_PATCH_LIST.md` through document change control.
4. Verify the ingestion manifest/checksums: exactly one preferred document per number 01–105.
5. Re-run the Phase-0 generation if any document changed.
