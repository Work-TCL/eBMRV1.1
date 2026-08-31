# WP-04 — UI Workflows

Frappe screens never write regulated state directly; each action calls a GxP API operation. Projected GxP fields are read-only.

| UI surface | Doc | Module |
|---|---|---|
| Supplier Catalogue | 18 | SPEC-MAT-001 |
| Supplier Qualification | 18 | SPEC-MAT-001 |
| Supplier Audit | 18 | SPEC-MAT-001 |
| Approved Supplier List | 18 | SPEC-MAT-001 |
| Material/Source Matrix | 18 | SPEC-MAT-001 |
| Supplier Performance | 18 | SPEC-MAT-001 |
| SCAR Links | 18 | SPEC-MAT-001 |
| RFQ/Quote Comparison | 18 | SPEC-MAT-001 |
| PO Regulated Requirements | 18 | SPEC-MAT-001 |
| Supplier Quality Dashboard | 18 | SPEC-MAT-001 |
| Expected Receipts | 19 | SPEC-MAT-002A |
| Receiving | 19 | SPEC-MAT-002A |
| Visual Examination | 19 | SPEC-MAT-002A |
| Lot/Container Labeling | 19 | SPEC-MAT-002A |
| Quarantine Dashboard | 19 | SPEC-MAT-002A |
| Sampling | 19 | SPEC-MAT-002A |
| QC/LIMS Status | 19 | SPEC-MAT-002A |
| Quality Disposition | 19 | SPEC-MAT-002A |
| Retest/Expiry Dashboard | 19 | SPEC-MAT-002A |
| Receipt History | 19 | SPEC-MAT-002A |
| Warehouse Overview | 20 | SPEC-MAT-002B |
| Material Availability | 20 | SPEC-MAT-002B |
| Lot/Container Search | 20 | SPEC-MAT-002B |
| Transfer | 20 | SPEC-MAT-002B |
| Reservation | 20 | SPEC-MAT-002B |
| Expiry/Retest | 20 | SPEC-MAT-002B |
| Quality Hold | 20 | SPEC-MAT-002B |
| Cycle Count | 20 | SPEC-MAT-002B |
| Container Split/Merge | 20 | SPEC-MAT-002B |
| Inventory Ledger | 20 | SPEC-MAT-002B |
| ERP Reconciliation | 20 | SPEC-MAT-002B |
| Dispensing Queue | 21 | SPEC-MAT-002C |
| Scan Batch/Requirement | 21 | SPEC-MAT-002C |
| Scan Source | 21 | SPEC-MAT-002C |
| Equipment/Booth Check | 21 | SPEC-MAT-002C |
| Target Calculation | 21 | SPEC-MAT-002C |
| Live Weight | 21 | SPEC-MAT-002C |
| Tolerance | 21 | SPEC-MAT-002C |
| Verification | 21 | SPEC-MAT-002C |
| Label | 21 | SPEC-MAT-002C |
| Completed Record | 21 | SPEC-MAT-002C |
| Batch Material Usage | 22 | SPEC-MAT-002D |
| Consume | 22 | SPEC-MAT-002D |
| Return | 22 | SPEC-MAT-002D |
| Loss/Spill/Sample | 22 | SPEC-MAT-002D |
| Adjustment Request | 22 | SPEC-MAT-002D |
| Destruction | 22 | SPEC-MAT-002D |
| Reconciliation | 22 | SPEC-MAT-002D |
| ERP Posting/Reconciliation | 22 | SPEC-MAT-002D |
| Material History | 22 | SPEC-MAT-002D |
| sample/source; | 23 | SPEC-QC-001 |
| method; | 23 | SPEC-QC-001 |
| sample amount; | 23 | SPEC-QC-001 |
| raw data/evidence; | 23 | SPEC-QC-001 |
| calculations; | 23 | SPEC-QC-001 |
| result/criterion; | 23 | SPEC-QC-001 |
| prior/superseded results; | 23 | SPEC-QC-001 |
| system suitability; | 23 | SPEC-QC-001 |
| OOS/OOT; | 23 | SPEC-QC-001 |
| analyst; | 23 | SPEC-QC-001 |
| audit; | 23 | SPEC-QC-001 |
| review signature. | 23 | SPEC-QC-001 |
| LIMS Instances | 24 | SPEC-QC-002 |
| Mapping | 24 | SPEC-QC-002 |
| Message Monitor | 24 | SPEC-QC-002 |
| Dead Letter Queue | 24 | SPEC-QC-002 |
| Reconciliation Differences | 24 | SPEC-QC-002 |
| Manual Mapping Resolution | 24 | SPEC-QC-002 |
| Result History | 24 | SPEC-QC-002 |
| Health Dashboard | 24 | SPEC-QC-002 |
| correct mapping; | 24 | SPEC-QC-002 |
| retry/replay exact stored message; | 24 | SPEC-QC-002 |
| acknowledge known duplicate; | 24 | SPEC-QC-002 |
| link external/internal IDs. | 24 | SPEC-QC-002 |
| OOS Header / Original Result | 25 | SPEC-QC-003 |
| Raw Data / Method | 25 | SPEC-QC-003 |
| Laboratory Investigation | 25 | SPEC-QC-003 |
| Assignable Cause Decision | 25 | SPEC-QC-003 |
| Manufacturing/Extended Investigation | 25 | SPEC-QC-003 |
| Retest Plan/Results | 25 | SPEC-QC-003 |
| Resample Plan/Results | 25 | SPEC-QC-003 |
| Impact Assessment | 25 | SPEC-QC-003 |
| CAPA/Change Links | 25 | SPEC-QC-003 |
| Final Disposition | 25 | SPEC-QC-003 |
| QA Closure | 25 | SPEC-QC-003 |
| Full Audit | 25 | SPEC-QC-003 |
| OOT Signal | 25 | SPEC-QC-003 |
| Trend Chart / Historical Context | 25 | SPEC-QC-003 |
| Investigation | 25 | SPEC-QC-003 |
| Impact/Action | 25 | SPEC-QC-003 |
