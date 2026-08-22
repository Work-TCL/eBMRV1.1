# WP-05 — UI Workflows

Frappe screens never write regulated state directly; each action calls a GxP API operation. Projected GxP fields are read-only.

| UI surface | Doc | Module |
|---|---|---|
| Deviation Dashboard | 26 | SPEC-QMS-001 |
| Initiation/Triage | 26 | SPEC-QMS-001 |
| Containment | 26 | SPEC-QMS-001 |
| Investigation & Evidence | 26 | SPEC-QMS-001 |
| Root Cause | 26 | SPEC-QMS-001 |
| Impact Assessment | 26 | SPEC-QMS-001 |
| Disposition | 26 | SPEC-QMS-001 |
| Linked CAPA/Change | 26 | SPEC-QMS-001 |
| QA Closure | 26 | SPEC-QMS-001 |
| Audit/History | 26 | SPEC-QMS-001 |
| CAPA Dashboard | 27 | SPEC-QMS-002 |
| Problem/Scope | 27 | SPEC-QMS-002 |
| Root Cause | 27 | SPEC-QMS-002 |
| Action Plan | 27 | SPEC-QMS-002 |
| Dependencies | 27 | SPEC-QMS-002 |
| Implementation Evidence | 27 | SPEC-QMS-002 |
| Effectiveness Plan | 27 | SPEC-QMS-002 |
| Effectiveness Review | 27 | SPEC-QMS-002 |
| QA Closure | 27 | SPEC-QMS-002 |
| Audit | 27 | SPEC-QMS-002 |
| NCR Dashboard | 28 | SPEC-QMS-003 |
| Initiation | 28 | SPEC-QMS-003 |
| Affected Scope | 28 | SPEC-QMS-003 |
| Segregation | 28 | SPEC-QMS-003 |
| Evaluation | 28 | SPEC-QMS-003 |
| Disposition | 28 | SPEC-QMS-003 |
| Rework/Retest | 28 | SPEC-QMS-003 |
| Supplier/CAPA Links | 28 | SPEC-QMS-003 |
| Closure | 28 | SPEC-QMS-003 |
| Audit | 28 | SPEC-QMS-003 |
| Change Dashboard | 29 | SPEC-QMS-004 |
| Request | 29 | SPEC-QMS-004 |
| Affected Objects | 29 | SPEC-QMS-004 |
| Impact Assessments | 29 | SPEC-QMS-004 |
| Risk | 29 | SPEC-QMS-004 |
| Implementation Plan | 29 | SPEC-QMS-004 |
| Validation/Training | 29 | SPEC-QMS-004 |
| Approvals | 29 | SPEC-QMS-004 |
| Execution Evidence | 29 | SPEC-QMS-004 |
| Post-Implementation Review | 29 | SPEC-QMS-004 |
| Closure | 29 | SPEC-QMS-004 |
| Document Library | 30 | SPEC-QMS-005 |
| Document Editor/Upload | 30 | SPEC-QMS-005 |
| Review/Approval | 30 | SPEC-QMS-005 |
| Version Compare | 30 | SPEC-QMS-005 |
| Effective/Obsolete | 30 | SPEC-QMS-005 |
| Controlled Copies | 30 | SPEC-QMS-005 |
| Periodic Review | 30 | SPEC-QMS-005 |
| Training Impact | 30 | SPEC-QMS-005 |
| Audit | 30 | SPEC-QMS-005 |
| Training Dashboard | 31 | SPEC-QMS-006 |
| Curriculum/Requirement | 31 | SPEC-QMS-006 |
| Assignments | 31 | SPEC-QMS-006 |
| Learning/Acknowledgment | 31 | SPEC-QMS-006 |
| Assessment | 31 | SPEC-QMS-006 |
| Practical Evaluation | 31 | SPEC-QMS-006 |
| Qualifications | 31 | SPEC-QMS-006 |
| Expiry/Renewal | 31 | SPEC-QMS-006 |
| Training Matrix | 31 | SPEC-QMS-006 |
| Transcript | 31 | SPEC-QMS-006 |
| Supplier Quality Dashboard | 32 | SPEC-QMS-007 |
| Supplier Case | 32 | SPEC-QMS-007 |
| Containment/ASL Impact | 32 | SPEC-QMS-007 |
| SCAR | 32 | SPEC-QMS-007 |
| Supplier Response | 32 | SPEC-QMS-007 |
| Internal Review | 32 | SPEC-QMS-007 |
| Effectiveness | 32 | SPEC-QMS-007 |
| Supplier Status | 32 | SPEC-QMS-007 |
| History | 32 | SPEC-QMS-007 |
| Risk Register | 33 | SPEC-QMS-008 |
| Risk Assessment | 33 | SPEC-QMS-008 |
| Controls/Mitigations | 33 | SPEC-QMS-008 |
| Residual Risk | 33 | SPEC-QMS-008 |
| Acceptance | 33 | SPEC-QMS-008 |
| Related Events/Changes | 33 | SPEC-QMS-008 |
| Review Calendar | 33 | SPEC-QMS-008 |
| Dashboard | 33 | SPEC-QMS-008 |
| Audit Program | 34 | SPEC-QMS-009 |
| Audit Plan | 34 | SPEC-QMS-009 |
| Checklist | 34 | SPEC-QMS-009 |
| Evidence/Notes | 34 | SPEC-QMS-009 |
| Findings | 34 | SPEC-QMS-009 |
| Report | 34 | SPEC-QMS-009 |
| Responses/CAPA | 34 | SPEC-QMS-009 |
| Follow-Up | 34 | SPEC-QMS-009 |
| Metrics | 34 | SPEC-QMS-009 |
| Complaint Intake | 35 | SPEC-QMS-010 |
| Product/Serial Lookup | 35 | SPEC-QMS-010 |
| Triage | 35 | SPEC-QMS-010 |
| Investigation Decision | 35 | SPEC-QMS-010 |
| Manufacturing/Genealogy Evidence | 35 | SPEC-QMS-010 |
| Returned Product | 35 | SPEC-QMS-010 |
| Reportability Assessment | 35 | SPEC-QMS-010 |
| CAPA/Field Action | 35 | SPEC-QMS-010 |
| Communications | 35 | SPEC-QMS-010 |
| Closure | 35 | SPEC-QMS-010 |
| Trend | 35 | SPEC-QMS-010 |
| Field Action Dashboard | 36 | SPEC-QMS-011 |
| Assessment/Risk | 36 | SPEC-QMS-011 |
| Affected Product Scope | 36 | SPEC-QMS-011 |
| Distribution/Consignees | 36 | SPEC-QMS-011 |
| Reportability | 36 | SPEC-QMS-011 |
| Communication Package | 36 | SPEC-QMS-011 |
| Execution | 36 | SPEC-QMS-011 |
| Returns/Corrections | 36 | SPEC-QMS-011 |
| Reconciliation | 36 | SPEC-QMS-011 |
| Effectiveness | 36 | SPEC-QMS-011 |
| Closure | 36 | SPEC-QMS-011 |
| Quality Dashboard | 37 | SPEC-QMS-012 |
| Metric Catalogue | 37 | SPEC-QMS-012 |
| Deviation/CAPA/OOS/NCR Trends | 37 | SPEC-QMS-012 |
| Complaint/Supplier Trends | 37 | SPEC-QMS-012 |
| Training/Audit Trends | 37 | SPEC-QMS-012 |
| Batch Quality | 37 | SPEC-QMS-012 |
| Alert Queue | 37 | SPEC-QMS-012 |
| Effectiveness Checks | 37 | SPEC-QMS-012 |
| Management Review Package | 37 | SPEC-QMS-012 |
