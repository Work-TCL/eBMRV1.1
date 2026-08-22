# WP-02 — Implementation Sequence

1. **Document 09 — Product, Constituent & Regulatory Profile Master**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-02/09_*.md`)
2. **Document 10 — Master Recipe / Master Manufacturing Record Specification**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-02/10_*.md`)
3. **Document 11 — Batch Execution Engine & State Machine Specification**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-02/11_*.md`)
4. **Document 12 — eDHR / Device Production History Specification**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-02/12_*.md`)

## Per-document notes from the specifications

### Document 09
```text
1. product family/draft;
2. constituent model;
3. profile completeness rules;
4. site admission;
5. compatibility version;
6. release to Vault;
7. projections;
8. external mapping;
9. suspension/reinstatement;
10. audit/export.
```
### Document 10
```text
1. recipe family/version;
2. sections/steps;
3. graph validation;
4. parameters;
5. materials/equipment;
6. rules/signatures;
7. QC/evidence;
8. profile validators;
9. release/Vault;
10. batch snapshot;
11. compare/simulation.
```
### Document 11
```text
1. batch aggregate/state;
2. issue snapshot;
3. step instances/readiness;
4. result capture;
5. completion;
6. signature/verifier;
7. holds/exceptions;
8. branches/parallel;
9. timers/Temporal;
10. material/equipment/QC adapters;
11. correction/rework;
12. production completion.
```
### Document 12
```text
see requirement order
```
