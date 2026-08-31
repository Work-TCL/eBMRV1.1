# WP-04 — Implementation Sequence

1. **Document 18 — Procurement & Supplier Quality Specification**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-04/18_*.md`)
2. **Document 19 — Material Receipt, Quarantine & Quality Status Specification**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-04/19_*.md`)
3. **Document 20 — Inventory, Lot/Container & Warehouse Specification**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-04/20_*.md`)
4. **Document 21 — Material Dispensing & Weighing Specification**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-04/21_*.md`)
5. **Document 22 — Material Consumption, Return, Adjustment, Destruction & Reconciliation Specification**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-04/22_*.md`)
6. **Document 23 — Native Basic QC & Sampling Specification**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-04/23_*.md`)
7. **Document 24 — LIMS Integration Architecture & Generic Adapter Contract**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-04/24_*.md`)
8. **Document 25 — OOS / OOT Management Specification**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-04/25_*.md`)

## Per-document notes from the specifications

### Document 18
```text
1. supplier/site;
2. qualification;
3. ASL/source matrix;
4. performance/expiry;
5. PR;
6. PO reference/native PO;
7. ERP adapter;
8. quality agreements;
9. suspension/change impact;
10. reports.
```
### Document 19
```text
1. receipt;
2. lot/container;
3. automatic quarantine;
4. labels;
5. sampling;
6. QC adapter;
7. release/reject;
8. retest;
9. ERP sync;
10. reports.
```
### Document 20
```text
see requirement order
```
### Document 21
```text
see requirement order
```
### Document 22
```text
1. consumption;
2. partial/remaining;
3. return;
4. samples/losses;
5. adjustments/reversal pattern;
6. destruction;
7. reconciliation;
8. ERP posting;
9. batch-completion integration.
```
### Document 23
```text
1. test specification/method references;
2. sample;
3. test order;
4. result schemas;
5. calculation/acceptance;
6. raw evidence;
7. analyst completion;
8. second-person review;
9. OOS/OOT hooks;
10. release readiness;
11. instrument/Edge adapters.
```
### Document 24
```text
1. provider interface;
2. instance registry;
3. mapping;
4. sample outbound;
5. result inbound;
6. idempotency/versioning;
7. result acceptance through Mutation Gateway;
8. dead letter;
9. reconciliation;
10. OOS/OOT ownership modes;
11. first real vendor adapter.
```
### Document 25
```text
1. OOS trigger/original result link;
2. laboratory investigation;
3. lab cause classification;
4. broader investigation;
5. retest plan;
6. resample plan;
7. impact/disposition;
8. closure/signature;
9. release blockers;
10. OOT rule/investigation;
11. LIMS ownership modes;
12. metrics/trending.
```
