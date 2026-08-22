# US eBMR / eDHR Regulated Manufacturing Platform
## Document 112 — Entity Schema Completion & Migration Contract Addendum — v1.0 APPROVED

**Specification ID:** SPEC-DATA-013
**Status:** APPROVED v1.0 (construction baseline) — approvers of record: Data Architect and the owning module owners
**Closes:** SG-011, SG-015
**Approval:** Approved by the Project Owner during construction review on 2026-08-21. A formal Part 11 signature record must be captured in the QMS against this version before validated release; the approval block below is the record of the construction decision.

**Primary Dependencies:** Document 70 (PostgreSQL architecture/aggregate baseline), Document 100 (migration standard), Document 06/07/54/58/59/60 (owning specifications), Document 108 (retention)

---

# 0. Why this document exists

The Database Gate prohibits writing a migration before columns, types, constraints, indexes, versioning and retention behaviour are defined. Twenty-three entities are named in the baseline with no field-level definition, and thirty-two entity-owning specifications state no migration behaviour. Without this addendum each work package would invent its own schema conventions on regulated tables.

# 1. Universal aggregate baseline (Document 70)

Every regulated table inherits:

```sql
id          uuid PRIMARY KEY,
tenant_id   uuid NOT NULL,
site_id     uuid NULL,
state       text NOT NULL,
version     bigint NOT NULL,
created_at  timestamptz NOT NULL,
updated_at  timestamptz NOT NULL
```

plus: row-level tenant scoping, optimistic concurrency on `version`, no in-place edit of released/immutable rows, an audit companion in the same transaction, and a retention class from Document 108.

# 2. Completed schemas


## `vault_object`

**Source:** Document 06 — VLT-FR-001/002/004/019/022

```sql
id uuid PK
tenant_id uuid NOT NULL
object_type varchar(60) NOT NULL          -- MasterRecipe | Specification | ControlledDocument | BatchRecord | DHR | RegulatoryReport
business_id varchar(120) NOT NULL         -- stable business identifier of the object
version bigint NOT NULL                   -- monotonic per (tenant_id, object_type, business_id)
status varchar(30) NOT NULL               -- RELEASED | SUPERSEDED | WITHDRAWN
canonical_form jsonb NOT NULL             -- canonical structured snapshot (VLT-FR-002)
digest_algorithm varchar(20) NOT NULL     -- e.g. SHA-256
digest varchar(128) NOT NULL              -- over canonical_form + manifest digest (VLT-FR-003)
dependency_closure jsonb NOT NULL         -- exact ids/versions/hashes of dependent released objects (VLT-FR-007)
effective_from timestamptz NULL
effective_to timestamptz NULL
release_reason text NULL
released_by uuid NOT NULL
release_signature_id uuid NULL
superseded_by_id uuid NULL REFERENCES vault_object(id)
retention_class_code varchar(40) NOT NULL -- Document 108
legal_hold boolean NOT NULL DEFAULT false
worm_locked_until timestamptz NULL
created_at timestamptz NOT NULL DEFAULT now()
```

**Constraints:** UNIQUE (tenant_id, object_type, business_id, version); CHECK (status IN ('RELEASED','SUPERSEDED','WITHDRAWN')); no UPDATE permitted except status/superseded_by/legal_hold via the Vault service (VLT-FR-012)

**Indexes:** (tenant_id, object_type, business_id, version DESC), (tenant_id, status), (digest)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `vault_evidence_manifest`

**Source:** Document 06 — VLT-FR-005/024; Document 72

```sql
id uuid PK
tenant_id uuid NOT NULL
vault_object_id uuid NOT NULL REFERENCES vault_object(id)
evidence_id uuid NOT NULL                 -- object-store evidence reference
content_digest varchar(128) NOT NULL      -- content addressing enables dedupe (VLT-FR-024)
media_type varchar(120) NOT NULL
byte_size bigint NOT NULL
evidence_role varchar(60) NOT NULL        -- ATTACHMENT | RENDERING | SOURCE_DATA | SIGNATURE_MANIFESTATION
source_reference jsonb NULL               -- originating record/device/system
sequence_no integer NOT NULL
created_at timestamptz NOT NULL DEFAULT now()
```

**Constraints:** UNIQUE (vault_object_id, sequence_no); UNIQUE (vault_object_id, evidence_id); append-only

**Indexes:** (tenant_id, content_digest), (vault_object_id)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `iam_qualification`

**Source:** Document 07 — IAM-FR-010/011/012/026/031

```sql
id uuid PK
tenant_id uuid NOT NULL
site_id uuid NULL
subject_id uuid NOT NULL
qualification_code varchar(80) NOT NULL   -- DISPENSING | STERILE_AREA | ASEPTIC_OPERATION | QA_RELEASE | EQUIPMENT_<class> ...
qualification_type varchar(40) NOT NULL   -- TRAINING | TASK_COMPETENCY | EQUIPMENT | AREA | ROLE
scope jsonb NULL                          -- equipment ids/classes, areas, product families
granted_by uuid NOT NULL
granted_signature_id uuid NULL
evidence_reference jsonb NULL             -- training record / assessment reference (Document 31)
valid_from timestamptz NOT NULL
valid_to timestamptz NULL                 -- NULL = no expiry; expiry-driven gating uses this
state varchar(30) NOT NULL                -- ACTIVE | EXPIRED | SUSPENDED | REVOKED
suspension_reason text NULL
version bigint NOT NULL
created_at timestamptz NOT NULL DEFAULT now()
```

**Constraints:** UNIQUE (tenant_id, subject_id, qualification_code, valid_from); CHECK (valid_to IS NULL OR valid_to > valid_from)

**Indexes:** (tenant_id, subject_id, state), (tenant_id, qualification_code, valid_to)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `ddcp_profile_version`

**Source:** Document 54 — PFS-FR-001/002/028/029

```sql
id uuid PK
tenant_id uuid NOT NULL
profile_code varchar(80) NOT NULL         -- e.g. PFS, AUTOINJECTOR, MDI, DPI, DRUG_ELUTING
subtype varchar(80) NULL
version bigint NOT NULL
state varchar(30) NOT NULL                -- DRAFT | RELEASED | SUPERSEDED
dosage_form varchar(80) NULL
presentation varchar(80) NULL
constituent_architecture jsonb NOT NULL   -- drug/biologic + device constituent definition
required_controls jsonb NOT NULL          -- steps, evidence, checks the profile adds
release_checkpoint_set jsonb NOT NULL
vault_object_id uuid NULL
released_by uuid NULL
release_signature_id uuid NULL
effective_from timestamptz NULL
created_at timestamptz NOT NULL DEFAULT now()
```

**Constraints:** UNIQUE (tenant_id, profile_code, version); released profiles are immutable

**Indexes:** (tenant_id, profile_code, state)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `constituent_requirement`

**Source:** Document 54 — PFS-FR-002/004/005/016

```sql
id uuid PK
tenant_id uuid NOT NULL
ddcp_profile_version_id uuid NOT NULL REFERENCES ddcp_profile_version(id)
constituent_type varchar(40) NOT NULL     -- DRUG | BIOLOGIC | DEVICE | PACKAGING | LABEL
component_role varchar(80) NOT NULL       -- barrel | stopper | plunger | needle | tip_cap | safety_device | bulk_drug
required_state varchar(60) NOT NULL       -- RELEASED | READY_TO_USE | STERILIZED | DEPYROGENATED
material_spec_reference jsonb NULL        -- specification id/version
attribute_requirements jsonb NULL         -- silicone/tungsten/particulate and similar profile attributes
mandatory boolean NOT NULL DEFAULT true
sequence_no integer NOT NULL
```

**Constraints:** UNIQUE (ddcp_profile_version_id, component_role, sequence_no)

**Indexes:** (ddcp_profile_version_id, constituent_type)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `constituent_handoff`

**Source:** Document 54 — PFS-FR-003, §8 handoff contract

```sql
id uuid PK
tenant_id uuid NOT NULL
batch_id uuid NOT NULL
from_constituent varchar(40) NOT NULL
to_constituent varchar(40) NOT NULL
source_batch_reference jsonb NOT NULL     -- released bulk/component batch id + version
attributes jsonb NOT NULL                 -- assay/potency, concentration, sterility/bioburden references
accepted_by uuid NOT NULL
acceptance_signature_id uuid NULL
accepted_at timestamptz NOT NULL
state varchar(30) NOT NULL                -- PENDING | ACCEPTED | REJECTED
rejection_reason text NULL
version bigint NOT NULL
```

**Constraints:** UNIQUE (batch_id, from_constituent, to_constituent, source_batch_reference->>'batch_id')

**Indexes:** (tenant_id, batch_id), (state)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `fill_operation`

**Source:** Document 54 — PFS-FR-006..011

```sql
id uuid PK
tenant_id uuid NOT NULL
batch_id uuid NOT NULL
line_id uuid NOT NULL
filler_equipment_id uuid NOT NULL
fill_program_id varchar(120) NOT NULL
fill_program_version varchar(40) NOT NULL
product_contact_path jsonb NOT NULL
target_fill numeric(18,6) NOT NULL
target_fill_uom varchar(20) NOT NULL
cycle_group varchar(80) NULL
started_at timestamptz NOT NULL
ended_at timestamptz NULL
line_readiness_reference jsonb NOT NULL   -- cleaning, SIP, EM, personnel, filter status references
machine_count_start bigint NULL
machine_count_end bigint NULL
interventions jsonb NULL
alarms jsonb NULL
state varchar(30) NOT NULL
version bigint NOT NULL
```

**Constraints:** CHECK (ended_at IS NULL OR ended_at >= started_at); CHECK (target_fill > 0)

**Indexes:** (tenant_id, batch_id), (line_id, started_at)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `production_count_ledger`

**Source:** Document 54 — PFS-FR-010/015/022

```sql
id uuid PK
tenant_id uuid NOT NULL
batch_id uuid NOT NULL
count_type varchar(60) NOT NULL           -- FILLED | REJECTED_VISUAL | REJECTED_IPC | SAMPLED | LINE_LOSS | PACKED
source varchar(40) NOT NULL               -- MACHINE | MANUAL | RECONCILIATION
quantity bigint NOT NULL
uom varchar(20) NOT NULL DEFAULT 'EA'
recorded_by uuid NULL                     -- NULL for machine-sourced with device reference
device_reference jsonb NULL
reason_code varchar(80) NULL
occurred_at timestamptz NOT NULL
correction_of_id uuid NULL REFERENCES production_count_ledger(id)
version bigint NOT NULL
```

**Constraints:** append-only ledger; corrections create a new superseding row (never UPDATE); CHECK (quantity >= 0)

**Indexes:** (tenant_id, batch_id, count_type), (occurred_at)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `device_assembly_record`

**Source:** Document 54 — PFS-FR-013/018/021

```sql
id uuid PK
tenant_id uuid NOT NULL
batch_id uuid NOT NULL
unit_identifier varchar(120) NULL         -- serial/UDI where unit-level tracking applies
assembly_step varchar(80) NOT NULL        -- NEEDLE_INSTALL | SHIELD | TIP_CAP | SAFETY_DEVICE | PLUNGER
component_lot_reference jsonb NOT NULL
equipment_id uuid NULL
process_parameters jsonb NULL
performed_by uuid NULL
performed_signature_id uuid NULL
verified_by uuid NULL
verified_signature_id uuid NULL
result varchar(30) NOT NULL               -- PASS | FAIL | REWORK
occurred_at timestamptz NOT NULL
version bigint NOT NULL
```

**Constraints:** CHECK (verified_by IS NULL OR verified_by <> performed_by)  -- IND-001 independence

**Indexes:** (tenant_id, batch_id), (unit_identifier)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `device_functional_test_link`

**Source:** Document 54 — PFS-FR-014/017

```sql
id uuid PK
tenant_id uuid NOT NULL
batch_id uuid NOT NULL
test_type varchar(80) NOT NULL            -- CCI | LEAK | SEAL | BREAK_LOOSE | GLIDE_FORCE | DOSE_DELIVERY | SHIELD_REMOVAL
qc_record_reference jsonb NOT NULL        -- owning QC/LIMS record id + version (never duplicated here)
sample_plan_reference jsonb NULL
method_reference jsonb NULL
result_state varchar(30) NOT NULL         -- PENDING | PASS | FAIL | OOS
blocks_release boolean NOT NULL DEFAULT true
linked_at timestamptz NOT NULL
version bigint NOT NULL
```

**Constraints:** UNIQUE (batch_id, test_type, qc_record_reference->>'record_id'); QC results are owned by Document 23/24, referenced only

**Indexes:** (tenant_id, batch_id, result_state)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `ddcp_release_checkpoint`

**Source:** Document 54 — PFS-FR-023/024

```sql
id uuid PK
tenant_id uuid NOT NULL
batch_id uuid NOT NULL
checkpoint_code varchar(80) NOT NULL      -- DRUG_CONSTITUENT | DEVICE_CONSTITUENT | COMBINED_PRODUCT
required_evidence jsonb NOT NULL
blocker_state jsonb NOT NULL              -- open deviations/OOS/EM/CCI/reconciliation blockers
state varchar(30) NOT NULL                -- OPEN | SATISFIED | BLOCKED | WAIVED_BY_APPROVAL
decided_by uuid NULL
decision_signature_id uuid NULL
decided_at timestamptz NULL
version bigint NOT NULL
```

**Constraints:** UNIQUE (batch_id, checkpoint_code); final combined-product release requires all checkpoints SATISFIED

**Indexes:** (tenant_id, batch_id, state)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `batch_evidence_manifest`

**Source:** Document 54 — PFS-FR-025/030; Document 72

```sql
id uuid PK
tenant_id uuid NOT NULL
batch_id uuid NOT NULL
manifest_version bigint NOT NULL
evidence_set jsonb NOT NULL               -- ordered evidence ids + digests included in the inspection package
digest varchar(128) NOT NULL
generated_by uuid NOT NULL
generated_at timestamptz NOT NULL
vault_object_id uuid NULL
state varchar(30) NOT NULL                -- DRAFT | FROZEN
version bigint NOT NULL
```

**Constraints:** UNIQUE (batch_id, manifest_version); frozen manifests are immutable

**Indexes:** (tenant_id, batch_id, state)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `postmarket_source`

**Source:** Document 58 — PMS-FR-001/003/004/005/026/027

```sql
id uuid PK
tenant_id uuid NOT NULL
source_type varchar(60) NOT NULL          -- COMPLAINT | SERVICE | REPAIR | LITERATURE | REGULATOR | DISTRIBUTOR | FIELD_ACTION | MANUFACTURING | QC | STUDY
source_record_reference jsonb NULL        -- owning QMS/service record id + version (never duplicated)
external_reference varchar(200) NULL
source_receipt_at timestamptz NULL
company_initial_receipt_at timestamptz NULL
system_ingest_at timestamptz NOT NULL
reporter_details jsonb NULL               -- minimum-necessary, encrypted/pseudonymised per PMS-FR-029
product_resolution jsonb NULL             -- product/application, lot/batch/serial, UDI/NDC, constituent architecture
identity_resolution_state varchar(30) NOT NULL  -- RESOLVED | UNKNOWN_QUEUE
citation jsonb NULL                       -- literature citation/reference
state varchar(30) NOT NULL
version bigint NOT NULL
```

**Constraints:** CHECK (identity_resolution_state <> 'UNKNOWN_QUEUE' OR product_resolution IS NULL); unknown identity is never discarded (PMS-FR-005)

**Indexes:** (tenant_id, source_type, system_ingest_at), (identity_resolution_state)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `safety_case_followup`

**Source:** Document 58 — PMS-FR-016/017

```sql
id uuid PK
tenant_id uuid NOT NULL
safety_case_id uuid NOT NULL
followup_version bigint NOT NULL
followup_receipt_at timestamptz NOT NULL
source_reference jsonb NOT NULL
new_information jsonb NOT NULL
reassessment_flags jsonb NOT NULL         -- seriousness/causality/expectedness/reportability re-evaluation triggers
expectedness_reference jsonb NULL         -- exact labelling/RSI version used (PMS-FR-017)
recorded_by uuid NOT NULL
recorded_at timestamptz NOT NULL
```

**Constraints:** UNIQUE (safety_case_id, followup_version); append-only, immutable once created

**Indexes:** (tenant_id, safety_case_id, followup_version DESC)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `safety_signal`

**Source:** Document 58 — PMS-FR-018..025

```sql
id uuid PK
tenant_id uuid NOT NULL
signal_code varchar(120) NOT NULL
detection_source varchar(40) NOT NULL     -- RULE | REVIEWER
rule_version varchar(40) NULL
population_definition jsonb NOT NULL      -- product/family/site/lot/device/constituent + time window
exposure_denominator jsonb NULL           -- distribution/exposure data + source cutoff/version
denominator_uncertain boolean NOT NULL DEFAULT false
case_snapshot jsonb NOT NULL              -- frozen case/evidence snapshot (PMS-FR-021)
assessment jsonb NULL
state varchar(30) NOT NULL                -- DETECTED | TRIAGE | ASSESSMENT | REFUTED | MONITORING | CONFIRMED | ACTION | CLOSED
escalation_links jsonb NULL               -- CAPA / Change / Risk / Field Action / reportability tracks
owner_subject_id uuid NULL
opened_at timestamptz NOT NULL
closed_at timestamptz NULL
version bigint NOT NULL
```

**Constraints:** UNIQUE (tenant_id, signal_code); state transitions server-controlled per PMS-FR-023

**Indexes:** (tenant_id, state, opened_at)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `reportability_track`

**Source:** Document 59 — REG-FR-001..013

```sql
id uuid PK
tenant_id uuid NOT NULL
safety_case_id uuid NOT NULL
report_type_code varchar(80) NOT NULL     -- MDR_30 | MDR_5 | MALFUNCTION | DRUG_EXPEDITED_15 | BIOLOGIC_EXPEDITED_15 | PART4_30 ...
report_type_version varchar(40) NOT NULL  -- effective-dated catalogue version (REG-FR-003)
application_context jsonb NOT NULL        -- NDA/ANDA/BLA/device application + applicant role
clock_start_basis varchar(80) NOT NULL    -- source receipt / company awareness / agency request
clock_start_at timestamptz NOT NULL
clock_start_rationale text NOT NULL
calendar_type varchar(20) NOT NULL        -- CALENDAR_DAY | WORK_DAY | WORKING_DAY | AGENCY_SPECIFIED
calendar_version varchar(40) NOT NULL
due_at timestamptz NOT NULL
original_due_at timestamptz NOT NULL
decision varchar(30) NULL                 -- REPORTABLE | NOT_REPORTABLE (human authority, REG-FR-004)
decision_by uuid NULL
decision_signature_id uuid NULL
decision_rationale text NULL
rule_version varchar(40) NOT NULL
parent_track_id uuid NULL REFERENCES reportability_track(id)  -- follow-up/supplemental
state varchar(30) NOT NULL
version bigint NOT NULL
```

**Constraints:** CHECK (due_at >= clock_start_at); original_due_at immutable after creation (REG-FR-005, PMO-FR-023)

**Indexes:** (tenant_id, state, due_at), (safety_case_id)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `regulatory_report`

**Source:** Document 59 — REG-FR-014..017/024

```sql
id uuid PK
tenant_id uuid NOT NULL
reportability_track_id uuid NOT NULL REFERENCES reportability_track(id)
report_version bigint NOT NULL
schema_code varchar(60) NOT NULL          -- canonical data-element schema
schema_version varchar(40) NOT NULL
content jsonb NOT NULL
field_provenance jsonb NOT NULL           -- per-field source trace (REG-FR-016)
missing_information jsonb NULL            -- unknown/not-obtained markers (REG-FR-015)
narrative_version bigint NULL
approved_by uuid NULL
approval_signature_id uuid NULL
payload_digest varchar(128) NULL
state varchar(30) NOT NULL                -- DRAFT | APPROVED | SUBMITTED | SUPERSEDED
created_at timestamptz NOT NULL
```

**Constraints:** UNIQUE (reportability_track_id, report_version); APPROVED/SUBMITTED versions are immutable (REG-FR-024)

**Indexes:** (tenant_id, state), (reportability_track_id, report_version DESC)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `regulatory_submission_attempt`

**Source:** Document 59 — REG-FR-018..023/025

```sql
id uuid PK
tenant_id uuid NOT NULL
regulatory_report_id uuid NOT NULL REFERENCES regulatory_report(id)
attempt_no integer NOT NULL
channel varchar(60) NOT NULL              -- EMDR | ESG_NEXTGEN | SRP | MANUAL
endpoint_profile varchar(120) NULL
payload_version varchar(40) NOT NULL
payload_digest varchar(128) NOT NULL
sender_identity varchar(120) NOT NULL     -- service identity for transport only; approval remains human
authorized_by uuid NOT NULL               -- human submission authorization (SIG-FR-023)
authorization_signature_id uuid NULL
attempted_at timestamptz NOT NULL
transport_result varchar(30) NOT NULL     -- SENT | FAILED | TIMEOUT_UNCERTAIN
failure_detail jsonb NULL
manual_evidence_id uuid NULL              -- for MANUAL channel (REG-FR-022)
```

**Constraints:** UNIQUE (regulatory_report_id, attempt_no); duplicate initial submission prevented by unique partial index on approved report version

**Indexes:** (tenant_id, attempted_at), (transport_result)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `regulatory_submission_ack`

**Source:** Document 59 — REG-FR-019/026

```sql
id uuid PK
tenant_id uuid NOT NULL
submission_attempt_id uuid NOT NULL REFERENCES regulatory_submission_attempt(id)
ack_level varchar(30) NOT NULL            -- TRANSPORT | PROCESSING | AGENCY_ACCEPTANCE
ack_state varchar(30) NOT NULL            -- ACCEPTED | REJECTED | PENDING
ack_reference varchar(200) NULL
ack_payload jsonb NULL
ack_received_at timestamptz NOT NULL
rejection_reason jsonb NULL
```

**Constraints:** append-only; transport success alone never sets AGENCY_ACCEPTANCE (REG-FR-019)

**Indexes:** (submission_attempt_id, ack_level), (tenant_id, ack_state)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `applicant_relationship`

**Source:** Document 60 — PMO-FR-001/002/006

```sql
id uuid PK
tenant_id uuid NOT NULL
product_version_reference jsonb NOT NULL  -- marketed DDCP product version
applicant_role varchar(60) NOT NULL       -- COMBINATION_PRODUCT_APPLICANT | CONSTITUENT_PART_APPLICANT
applicant_name varchar(200) NOT NULL
application_type varchar(40) NULL         -- NDA | ANDA | BLA | PMA | 510K
application_number varchar(60) NULL
address jsonb NOT NULL
contact jsonb NOT NULL
sharing_channel varchar(80) NULL
valid_from timestamptz NOT NULL
valid_to timestamptz NULL
version bigint NOT NULL
```

**Constraints:** UNIQUE (tenant_id, product_version_reference->>'product_version_id', applicant_role, applicant_name, valid_from)

**Indexes:** (tenant_id, applicant_role), (application_number)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `constituent_information_share`

**Source:** Document 60 — PMO-FR-003..008

```sql
id uuid PK
tenant_id uuid NOT NULL
safety_case_id uuid NOT NULL
applicant_relationship_id uuid NOT NULL REFERENCES applicant_relationship(id)
applicant_relationship_version bigint NOT NULL
company_receipt_at timestamptz NOT NULL
due_at timestamptz NOT NULL               -- no later than 5 calendar days (PMO-FR-004)
package_content jsonb NOT NULL            -- frozen shared information (PMO-FR-005)
package_digest varchar(128) NOT NULL
package_version bigint NOT NULL
shared_at timestamptz NULL
shared_by uuid NULL
sharing_signature_id uuid NULL
delivery_evidence jsonb NULL
state varchar(30) NOT NULL                -- PENDING | SHARED | FAILED | ESCALATED
version bigint NOT NULL
```

**Constraints:** CHECK (due_at > company_receipt_at); package immutable once created; corrections create a new package_version

**Indexes:** (tenant_id, state, due_at), (safety_case_id)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `correction_removal_regulatory_record`

**Source:** Document 60 — PMO-FR-009..012/030

```sql
id uuid PK
tenant_id uuid NOT NULL
field_action_reference jsonb NOT NULL      -- exact Document 36 field-action id + scope snapshot version
assessment_state varchar(40) NOT NULL      -- REPORTABLE | NON_REPORTABLE
regime varchar(40) NOT NULL                -- PART_806_REPORT | PART_806_20_RECORD
initiation_at timestamptz NOT NULL
due_at timestamptz NULL                    -- 10 working days when reportable (PMO-FR-010)
calendar_version varchar(40) NULL
required_facts jsonb NOT NULL              -- source/action facts required by the applicable rule
decision_by uuid NULL
decision_signature_id uuid NULL
scope_amendments jsonb NULL                -- lot/batch expansion amendments (PMO-FR-012)
retention_class_code varchar(40) NOT NULL  -- RC-806 (Document 108)
state varchar(30) NOT NULL
version bigint NOT NULL
```

**Constraints:** CHECK (regime <> 'PART_806_REPORT' OR due_at IS NOT NULL); field-action execution data is referenced, never duplicated

**Indexes:** (tenant_id, state, due_at)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


## `periodic_reporting_cycle`

**Source:** Document 60 — PMO-FR-017..019/031

```sql
id uuid PK
tenant_id uuid NOT NULL
application_reference jsonb NOT NULL
cycle_type varchar(40) NOT NULL            -- QUARTERLY | ANNUAL | FDA_CONFIGURED
period_start timestamptz NOT NULL
period_end timestamptz NOT NULL
data_cutoff_at timestamptz NOT NULL
dataset_snapshot_id uuid NULL              -- immutable Document 58 interval dataset
inclusion_rules_version varchar(40) NOT NULL
part4_augmentation_required boolean NOT NULL DEFAULT false
state varchar(30) NOT NULL                 -- SCHEDULED | DATA_COLLECTION | FROZEN | ANALYSIS | APPROVED | SUBMITTED | ACK | ARCHIVE
approved_by uuid NULL
approval_signature_id uuid NULL
submission_reference jsonb NULL
version bigint NOT NULL
```

**Constraints:** UNIQUE (tenant_id, application_reference->>'application_number', cycle_type, period_start); frozen datasets immutable

**Indexes:** (tenant_id, state, period_end)

**Concurrency:** optimistic on `version` where mutable; append-only tables reject UPDATE.  
**Retention:** class assigned per Document 108 at creation.  
**Projection:** Frappe read model permitted, read-only, stamped with source id/version.


# 3. Migration contract defaults (closes SG-015)

Every entity-owning specification that states no migration behaviour inherits this contract:

| Aspect | Default rule |
|---|---|
| Compatibility window | Expand → migrate → contract. Two releases minimum between expand and contract. |
| Additive change | New nullable column or new table, deployed before the code that uses it. |
| Destructive change | Never in a single release; requires an approved data-migration plan (Document 87) and reconciliation evidence. |
| Backfill | Batched, resumable, idempotent, with progress and reconciliation counts recorded. |
| Lock risk | Any migration that takes an ACCESS EXCLUSIVE lock on a table above the declared row threshold requires a documented online strategy. |
| Rollback | Every migration has a tested rollback or a documented forward-fix rationale. |
| Regulated data | Regulated rows are never rewritten by a migration without an approved change record; corrections use the application correction path (Document 06). |
| Evidence | Migration execution evidence (plan, checksum, counts before/after, duration, operator) retained per RC-VALIDATION. |
| Ownership | Only the owning service migrates its own tables; cross-service schema writes are prohibited. |

Documents inheriting this default contract: 31, 32, 33, 34, 35, 36, 37, 54, 58, 59, 60, 61, 62, 63, 64, 66, 67, 68, 75, 76, 78, 80, 82, 84, 85, 86, 88, 90, 91, 92, 93, 94

# 4. Functional requirements

| ID | Requirement | Detailed behaviour | Acceptance intent |
|---|---|---|---|
| SCH-FR-001 | No migration without schema | A migration may not be written for an entity absent from the data model catalogue. | CI check against `04_DATA_MODEL_CATALOGUE.md`. |
| SCH-FR-002 | Aggregate baseline | Every regulated table carries the universal columns. | Static schema test. |
| SCH-FR-003 | Append-only enforcement | Append-only tables reject UPDATE/DELETE at the database privilege level, not only in code. | Privilege test. |
| SCH-FR-004 | Independence constraints | Where a schema encodes an independence rule (e.g. verifier ≠ performer) the constraint exists in the database as well as the policy engine. | Negative insert test. |
| SCH-FR-005 | Reference not duplication | Postmarket and DDCP tables reference owning QC/QMS/genealogy records; they never copy them. | Schema review + test. |
| SCH-FR-006 | Retention at creation | Insert without a retention class fails. | Negative test. |
| SCH-FR-007 | Migration contract | Every entity has a migration catalogue entry before its first migration. | Gate check. |

# 5. Acceptance criteria

1. All 23 entities have approved schemas before their first migration.
2. Every entity appears in `36_DATABASE_MIGRATION_CATALOGUE.md` with owner, compatibility window and rollback.
3. Append-only and independence constraints proven by negative tests at the database layer.

# 6. Claude Code / Codex prohibitions

- Do not create a table that is not in the data model catalogue.
- Do not store a regulated numeric quantity as `float`/`real`/`double precision` (Document 110).
- Do not duplicate a QC, genealogy, audit or equipment record into a profile or postmarket table.
- Do not add a nullable "temporary" column to a regulated table to avoid a migration plan.

# 7. Approval block

| Role | Name | Decision | Date | Signature reference |
|---|---|---|---|---|
| Data Architect |  |  |  |  |
| Module owner (Doc 06/07) |  |  |  |  |
| Module owner (Doc 54) |  |  |  |  |
| Module owner (Docs 58–60) |  |  |  |  |
