# 04 — Data Model Catalogue

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Every data entity declared in Documents 01–105 with owner, authoritative store, fields and completion status.

---

Field lists are reproduced from the controlled specifications. Entities marked `SCHEMA NOT SPECIFIED` require full column/type/constraint definition before any migration may be written (Database Gate, construction instruction §8).


## Document 02 — System Architecture & GxP Core Technical Specification (DOC-002)

**Owner service:** `docs/architecture` | **Authoritative store:** n/a (standard / governance document)

### `Purpose`

```text
uncontrolled Frappe database updates;
direct integration writes;
UI-only validation;
unsigned approval changes;
missing reason-for-change;
state transition bypass;
inconsistent audit creation.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `docs/architecture` (Doc 100)
- Source: Document 02

### `Modules`

```text
deviation;
CAPA;
OOS;
OOT;
nonconformance;
change control;
SCAR;
complaint;
recall/field action;
internal audit;
risk.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `docs/architecture` (Doc 100)
- Source: Document 02

### `Storage`

```text
AWS S3;
Azure Blob;
on-prem S3-compatible/object storage.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `docs/architecture` (Doc 100)
- Source: Document 02

### `Store`

```text
authoritative UTC timestamp;
original device/source timestamp where applicable;
local timezone identifier;
receive timestamp;
clock-quality metadata for Edge/device sources.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `docs/architecture` (Doc 100)
- Source: Document 02

### `Controls`

```text
NTP/time-sync monitoring;
clock drift alarm;
no browser-supplied authoritative time;
DST only affects display, not stored chronology;
Edge queues retain original source time + sequence.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `docs/architecture` (Doc 100)
- Source: Document 02

### `Inputs`

```text
all required steps complete;
required signatures valid;
QC complete;
unresolved deviation status;
unresolved OOS/OOT status;
material reconciliation;
yield;
equipment qualification;
personnel qualification;
environmental/sterile evidence;
label/packaging reconciliation;
genealogy completeness;
required documents/evidence;
customer/product-specific release rules.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `docs/architecture` (Doc 100)
- Source: Document 02

### `Outputs`

```text
eligible for release;
blocked with machine-readable reasons;
hold;
reject;
rework/reprocess route;
destruction;
other configured controlled disposition.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `docs/architecture` (Doc 100)
- Source: Document 02

### `Rules`

```text
no ERP-specific code inside batch domain;
mapping tables are versioned;
integration errors visible;
retries idempotent;
financial fields do not become GxP truth unless explicitly configured;
GxP consumption evidence remains independently retrievable.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `docs/architecture` (Doc 100)
- Source: Document 02

### `Authentication`

```text
SSO via OIDC/SAML;
MFA policy;
regulated signature step-up;
no shared accounts;
workload identities;
device certificates.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `docs/architecture` (Doc 100)
- Source: Document 02

### `Authorization`

```text
RBAC;
resource/site scope;
qualification;
SoD;
contextual policy;
least privilege.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `docs/architecture` (Doc 100)
- Source: Document 02

### `Network`

```text
TLS;
private DB subnets;
restricted east-west paths;
ingress/API gateway;
egress controls;
Edge mTLS.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `docs/architecture` (Doc 100)
- Source: Document 02

### `Secrets`

```text
cloud secret manager or on-prem vault abstraction;
rotation;
no secrets in repository;
no secrets in container images;
no passwords in logs.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `docs/architecture` (Doc 100)
- Source: Document 02

### `Encryption`

```text
TLS in transit;
encryption at rest;
backup encryption;
object-storage encryption;
managed keys;
optional customer-managed keys.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `docs/architecture` (Doc 100)
- Source: Document 02

### `Signals`

```text
application logs;
security logs;
metrics;
traces;
audit-health metrics;
integration health;
queue depth;
Temporal workflow health;
Edge buffer health;
DB health;
storage health;
backup health.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `docs/architecture` (Doc 100)
- Source: Document 02

### `Accessibility`

```text
keyboard operation;
clear validation feedback;
non-color-only status indication;
scalable text;
accessible form labels.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `docs/architecture` (Doc 100)
- Source: Document 02

### `Output`

```text
human-readable PDF;
structured JSON/XML where configured;
audit trail;
signature manifest;
attachment manifest;
machine evidence manifest;
checksums;
export manifest.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `docs/architecture` (Doc 100)
- Source: Document 02


## Document 03 — GxP Mutation Gateway (SPEC-GXP-001)

**Owner service:** `services/gxp-api/src/modules/mutation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `CommandReceipt`

```text
command_id
command_type
aggregate_id
previous_version
resulting_version
decision
audit_event_id
signature_id(s)
record_hash
correlation_id
committed_at_utc
projection_status
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/mutation` (Doc 100)
- Source: Document 03

### `IdempotencyRecord`

```text
tenant/site/source
idempotency_key
command_hash
first_seen_at
resulting_command_id
resulting_version
status
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/mutation` (Doc 100)
- Source: Document 03

### `OutboxEvent`

```text
event_id
topic/type
schema_version
aggregate/version
payload/reference
publish_attempts
published_at
next_retry_at
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/mutation` (Doc 100)
- Source: Document 03

### `gxp_command_receipt`

```text
command_id uuid PK
tenant_id uuid NOT NULL
site_id uuid NOT NULL
command_type varchar(120) NOT NULL
schema_version varchar(20) NOT NULL
aggregate_type varchar(80) NOT NULL
aggregate_id uuid NOT NULL
expected_version bigint
resulting_version bigint
idempotency_key varchar(200)
request_hash char(64)
status varchar(40) NOT NULL
audit_event_id uuid
correlation_id uuid NOT NULL
causation_id uuid
record_hash char(64)
error_code varchar(80)
created_at timestamptz NOT NULL
committed_at timestamptz
unique (tenant_id, command_id);
unique partial (tenant_id, idempotency_key) when key not null;
(tenant_id, aggregate_type, aggregate_id, created_at desc);
(correlation_id).
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/mutation` (Doc 100)
- Source: Document 03

### `gxp_outbox`

```text
event_id uuid PK
tenant_id uuid NOT NULL
topic varchar(160) NOT NULL
event_type varchar(160) NOT NULL
schema_version varchar(20) NOT NULL
aggregate_type varchar(80)
aggregate_id uuid
aggregate_version bigint
payload jsonb NOT NULL
correlation_id uuid
causation_id uuid
created_at timestamptz NOT NULL
published_at timestamptz
attempt_count int NOT NULL default 0
next_attempt_at timestamptz
last_error text
(published_at, next_attempt_at);
(tenant_id, aggregate_id, created_at).
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/mutation` (Doc 100)
- Source: Document 03


## Document 04 — 21 CFR Part 11 Electronic Signature (SPEC-GXP-002)

**Owner service:** `services/gxp-api/src/modules/signature` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `gxp_signature_challenge`

```text
challenge_id uuid PK
tenant_id uuid NOT NULL
site_id uuid NOT NULL
signer_subject_id varchar(255) NOT NULL
record_type varchar(80) NOT NULL
record_id uuid NOT NULL
record_version bigint NOT NULL
record_hash char(64) NOT NULL
command_id uuid NOT NULL
action varchar(120) NOT NULL
meaning_code varchar(80) NOT NULL
required_auth_policy varchar(80) NOT NULL
nonce_hash char(64) NOT NULL
status varchar(40) NOT NULL
created_at timestamptz NOT NULL
expires_at timestamptz NOT NULL
verified_at timestamptz
consumed_at timestamptz
unique `(command_id, meaning_code, signer_subject_id)` where policy requires one signature.
```

**Indexes (source):** - (tenant_id, signer_subject_id, status, expires_at);

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/signature` (Doc 100)
- Source: Document 04

### `gxp_signature`

```text
signature_id uuid PK
challenge_id uuid UNIQUE NOT NULL
tenant_id uuid NOT NULL
site_id uuid NOT NULL
signer_subject_id varchar(255) NOT NULL
signer_display_name varchar(255) NOT NULL
record_type varchar(80) NOT NULL
record_id uuid NOT NULL
record_version bigint NOT NULL
record_hash char(64) NOT NULL
command_id uuid NOT NULL
action varchar(120) NOT NULL
meaning_code varchar(80) NOT NULL
executed_at timestamptz NOT NULL
idp_issuer varchar(500) NOT NULL
idp_session_ref varchar(255)
auth_time timestamptz
amr jsonb
acr varchar(255)
signature_service_version varchar(40) NOT NULL
policy_version varchar(80) NOT NULL
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/signature` (Doc 100)
- Source: Document 04


## Document 06 — Record Version Vault, Locking, Amendment & Controlled Correction (SPEC-GXP-004)

**Owner service:** `services/gxp-api/src/modules/vault` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `vault_object`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/vault` (Doc 100)
- Source: Document 06

### `vault_evidence_manifest`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/vault` (Doc 100)
- Source: Document 06

### `gxp_vault_object`

```text
object_id uuid PK
tenant_id uuid NOT NULL
site_id uuid
object_type varchar(80) NOT NULL
business_id varchar(160) NOT NULL
internal_version bigint NOT NULL
business_version_label varchar(80)
schema_version varchar(30) NOT NULL
canonical_payload jsonb NOT NULL
digest_algorithm varchar(40) NOT NULL
digest char(64) NOT NULL
status varchar(40) NOT NULL
effective_from timestamptz
effective_to timestamptz
supersedes_object_id uuid
corrected_from_object_id uuid
retention_class varchar(80)
released_at timestamptz NOT NULL
created_by_subject varchar(255)
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/vault` (Doc 100)
- Source: Document 06

### `gxp_vault_evidence`

```text
id uuid PK
vault_object_id uuid NOT NULL
evidence_id uuid NOT NULL
evidence_version bigint NOT NULL
evidence_sha256 char(64) NOT NULL
media_type varchar(120)
sequence int
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/vault` (Doc 100)
- Source: Document 06

### `gxp_record_correction`

```text
correction_id uuid PK
tenant_id uuid
record_object_id uuid NOT NULL
status varchar(40)
reason_code varchar(80)
reason_text text
impact_assessment jsonb
requested_by varchar(255)
approved_by_signatures jsonb
resulting_object_id uuid
created_at timestamptz
completed_at timestamptz
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/vault` (Doc 100)
- Source: Document 06


## Document 07 — Identity, Authorization, RBAC, Qualification & Segregation-of-Duties (SPEC-IAM-001)

**Owner service:** `services/gxp-api/src/modules/policy` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `iam_subject`

```text
subject_id uuid PK
tenant_id uuid NOT NULL
external_issuer varchar(500)
external_subject varchar(255)
display_name varchar(255)
email varchar(320)
subject_type varchar(40) NOT NULL
status varchar(40) NOT NULL
identity_verified boolean
signing_entitled boolean
created_at timestamptz
disabled_at timestamptz
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/policy` (Doc 100)
- Source: Document 07

### `iam_role_assignment`

```text
assignment_id uuid PK
tenant_id uuid
subject_id uuid
role_code varchar(100)
scope_type varchar(40)
scope_id uuid
effective_from timestamptz
expires_at timestamptz
status varchar(40)
approved_by_reference uuid
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/policy` (Doc 100)
- Source: Document 07

### `iam_qualification`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/policy` (Doc 100)
- Source: Document 07

### `iam_temporary_authorization`

```text
granted permissions;
approving signature;
review status.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/policy` (Doc 100)
- Source: Document 07


## Document 08 — Regulatory Rules & Calculation Engine (SPEC-GXP-006)

**Owner service:** `services/gxp-api/src/modules/rules` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `gxp_rule_definition`

```text
rule_object_id uuid PK
tenant_id uuid
rule_id varchar(160) NOT NULL
rule_type varchar(60) NOT NULL
semantic_version varchar(40) NOT NULL
schema_version varchar(20) NOT NULL
scope jsonb NOT NULL
status varchar(40) NOT NULL
effective_from timestamptz
effective_to timestamptz
expression_ast jsonb NOT NULL
input_contract jsonb NOT NULL
output_contract jsonb NOT NULL
unit_policy jsonb
precision_policy jsonb
rounding_policy jsonb
reason_codes jsonb
engine_compatibility varchar(80)
released_vault_object_id uuid
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/rules` (Doc 100)
- Source: Document 08

### `gxp_rule_evaluation`

```text
evaluation_id uuid PK
tenant_id uuid
rule_object_id uuid NOT NULL
aggregate_type varchar(80)
aggregate_id uuid
aggregate_version bigint
input_hash char(64)
inputs_or_refs jsonb
result jsonb NOT NULL
outcome varchar(40)
evaluated_at timestamptz
engine_version varchar(40)
correlation_id uuid
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/rules` (Doc 100)
- Source: Document 08


## Document 09 — Product, Constituent & Regulatory Profile Master (SPEC-EBMR-000)

**Owner service:** `services/gxp-api/src/modules/ebmr` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `product_family`

```text
id uuid PK
tenant_id uuid
family_code varchar(80)
name varchar(255)
profile_code varchar(80)
status varchar(40)
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 09

### `product_version`

```text
id uuid PK
tenant_id uuid NOT NULL
product_business_id varchar(120) NOT NULL
version_no bigint NOT NULL
product_code varchar(120) NOT NULL
name varchar(255) NOT NULL
product_family_id uuid
lifecycle_state varchar(40) NOT NULL
manufacturing_profile_code varchar(80) NOT NULL
combination_product_type varchar(40)
pmoa_reference varchar(255)
part4_profile_code varchar(80)
sterile_profile_id uuid
finished_tracking_strategy varchar(40)
udi_applicable boolean
strength_value numeric(24,8)
strength_uom varchar(40)
device_model_code varchar(120)
effective_from timestamptz
effective_to timestamptz
released_vault_object_id uuid
version_hash char(64)
created_at timestamptz
(tenant_id, product_business_id, version_no)
(tenant_id, product_code, version_no)
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 09

### `product_constituent`

```text
id uuid PK
product_version_id uuid NOT NULL
constituent_type varchar(40) NOT NULL
role_code varchar(40)
constituent_business_id varchar(120) NOT NULL
constituent_version_id uuid NOT NULL
source_site_id uuid
tracking_strategy varchar(40)
sequence_no int
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 09

### `constituent_compatibility_version`

```text
id uuid PK
tenant_id uuid
compatibility_code varchar(120)
version_no bigint
drug_constituent_version_id uuid
device_constituent_version_id uuid
interface_constraints jsonb
status varchar(40)
effective_from timestamptz
effective_to timestamptz
vault_object_id uuid
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 09

### `product_site_admission`

```text
product_version_id
site_id
operations allowed: manufacture/assemble/package/test/release
effective dates
status
approval reference
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 09

### `product_external_mapping`

```text
system_type
system_instance_id
product_version/business ID
external_id
mapping status/version
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 09


## Document 10 — Master Recipe / Master Manufacturing Record Specification (SPEC-EBMR-001)

**Owner service:** `services/gxp-api/src/modules/ebmr` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `recipe_family`

```text
id
tenant
product_business_id
recipe_code
site scope
manufacturing profile
lifecycle
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 10

### `recipe_version`

```text
id uuid PK
recipe_family_id uuid NOT NULL
version_no bigint NOT NULL
product_version_id uuid NOT NULL
site_id uuid NOT NULL
batch_size_value numeric(24,8)
batch_size_uom varchar(40)
status varchar(40)
effective_from/to
graph_version varchar(20)
released_vault_object_id uuid
digest char(64)
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 10

### `recipe_section`

```text
id
recipe_version_id
stable_section_code
name
sequence
area_requirement_id
parallel_group
expected_duration
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 10

### `recipe_step`

```text
id uuid PK
recipe_version_id uuid
stable_step_code varchar(120)
section_id uuid
step_type varchar(60)
instruction_markdown/text
sequence_hint int
required_role_code
qualification_policy_id
signature_policy_id
exception_policy_id
is_critical boolean
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 10

### `recipe_step_dependency`

```text
predecessor_step_id
successor_step_id
condition_rule_id/version
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 10

### `recipe_parameter`

```text
step_id
parameter_code
data_type
uom
source_type
target/min/max
precision
required
rule_id/version
manual_fallback_policy
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 10

### `recipe_material_requirement`

```text
step_id
material_spec_version_id
target quantity/formula reference
tolerance rule
alternative policy
consume mode
genealogy required
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 10

### `recipe_equipment_requirement`

```text
step_id
equipment class
exact equipment optional
calibration/qualification/cleaning policies
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 10

### `recipe_evidence_requirement`

```text
step_id
evidence type
required count
allowed MIME/file source
retention class
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 10


## Document 11 — Batch Execution Engine & State Machine Specification (SPEC-EBMR-002)

**Owner service:** `services/gxp-api/src/modules/ebmr` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `gxp_batch`

```text
id uuid PK
tenant_id uuid
site_id uuid
batch_number varchar(120)
product_version_id uuid
recipe_vault_object_id uuid
execution_snapshot_id uuid
target_qty numeric(24,8)
target_uom varchar(40)
state varchar(50)
version bigint NOT NULL
production_order_ref varchar(160)
created_at timestamptz
issued_at timestamptz
started_at timestamptz
production_completed_at timestamptz
qa_review_started_at timestamptz
closed_at timestamptz
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 11

### `gxp_batch_step`

```text
id uuid PK
batch_id uuid
recipe_step_code varchar(120)
scope_type varchar(40)
scope_id uuid
state varchar(40)
version bigint
assigned_subject_id uuid
started_at timestamptz
completed_at timestamptz
branch_status varchar(40)
exception_state varchar(40)
temporal_workflow_ref varchar(255)
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 11

### `gxp_step_result`

```text
step_id
parameter_code
result_version
value_decimal/text/bool/json
uom
source_type
source_id
source_timestamp
received_at
data_quality
rule_evaluation_id
created_by
supersedes_result_id
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 11

### `gxp_step_evidence_link`

```text
step
evidence ID/version/hash
requirement code
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 11

### `gxp_batch_hold`

```text
scope
reason
quality event
started/ended
signatures
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 11


## Document 12 — eDHR / Device Production History Specification (SPEC-EBMR-003)

**Owner service:** `services/gxp-api/src/modules/ebmr` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `device_unit`

```text
id uuid PK
tenant_id uuid
site_id uuid
product_version_id uuid
batch_id uuid
device_lot_id uuid
serial_number varchar(200)
udi_di varchar(120)
udi_pi jsonb
state varchar(40)
version bigint
release_status varchar(40)
created_at timestamptz
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 12

### `device_component_usage`

```text
parent_unit/subassembly ID
component type
component material lot
component serial
quantity
assembly step
timestamp
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 12

### `device_test_result`

```text
unit/lot scope
test specification version
test code
tester equipment ID
result values
pass/fail
raw evidence reference
rule evaluation
result version/supersession
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 12

### `device_defect`

```text
defect code
severity/classification
location
inspection/test source
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 12

### `device_evidence_inheritance`

```text
child unit
shared source record
evidence type
immutable source version/hash
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 12


## Document 13 — Genealogy & Traceability Engine Specification (SPEC-EBMR-004)

**Owner service:** `services/gxp-api/src/modules/ebmr` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `genealogy_node`

```text
id uuid PK
tenant_id uuid
node_type varchar(60)
business_ref varchar(200)
authoritative_record_type varchar(80)
authoritative_record_id uuid
authoritative_version bigint
record_hash char(64)
site_id uuid
created_at timestamptz
```

**Indexes (source):** - (tenant_id, node_type, business_ref)

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 13

### `genealogy_edge`

```text
id uuid PK
tenant_id uuid
from_node_id uuid NOT NULL
to_node_id uuid NOT NULL
edge_type varchar(60) NOT NULL
quantity numeric(24,8)
uom varchar(40)
step_id uuid
source_event_id uuid
state varchar(30) default 'ACTIVE'
supersedes_edge_id uuid
created_at timestamptz
```

**Indexes (source):** - (tenant_id, from_node_id, edge_type)

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 13


## Document 14 — Review-by-Exception & QA Review Specification (SPEC-EBMR-005)

**Owner service:** `services/gxp-api/src/modules/ebmr` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `qa_review_package`

```text
id uuid PK
tenant_id uuid
batch_id uuid
batch_version bigint
record_hash char(64)
checklist_version_id uuid
exception_index_version bigint
completeness_status varchar(40)
state varchar(40)
version bigint
created_at timestamptz
completed_at timestamptz
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 14

### `qa_review_item`

```text
package ID
category
source record/event
severity
status
assigned reviewer
disposition
comment
evidence refs
completed signature
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 14

### `qa_review_comment`

```text
exact source object/version
author
text
timestamp
status
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 14


## Document 15 — Release / Disposition Engine Specification (SPEC-EBMR-006)

**Owner service:** `services/gxp-api/src/modules/ebmr` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `release_scope`

```text
id uuid PK
tenant_id uuid
site_id uuid
scope_type varchar(40)
scope_id uuid
product_version_id uuid
batch_id uuid
state varchar(40)
version bigint
current_evaluation_id uuid
released_vault_object_id uuid
created_at timestamptz
decision_at timestamptz
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 15

### `release_evaluation`

```text
scope/version
rule set version
evaluated batch/source version
blockers JSON/reference
warnings
eligible bool
evaluation time
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 15

### `release_decision`

```text
exact scope
evaluation ID
decision code
reason/comment
signature ID
decision time
release package hash
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 15


## Document 16 — Packaging, Labeling & Reconciliation Specification (SPEC-EBMR-007)

**Owner service:** `services/gxp-api/src/modules/ebmr` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `packaging_run`

```text
batch ID
product/package configuration version
line/equipment
state/version
start/end
reconciliation state
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 16

### `label_issue`

```text
id uuid PK
tenant_id uuid
packaging_run_id uuid
label_version_id uuid
quantity_issued bigint
serial_range/reference jsonb
print_job_id uuid
issued_by/source
issued_at timestamptz
state varchar(40)
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 16

### `label_reconciliation`

```text
issued
applied/used
returned
destroyed
rejected
samples
calculated variance
tolerance rule
result
investigation link
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 16

### `package_node`

```text
package level
product/batch
parent package
state
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 16


## Document 17 — Yield, Calculations & Manufacturing Reconciliation Specification (SPEC-EBMR-008)

**Owner service:** `services/gxp-api/src/modules/ebmr` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `manufacturing_calculation`

```text
id uuid PK
tenant_id uuid
batch_id uuid
scope_type varchar(40)
scope_id uuid
calculation_type varchar(60)
phase_code varchar(80)
rule_object_id uuid
input_refs jsonb
input_hash char(64)
result jsonb
outcome varchar(40)
version bigint
evaluated_at timestamptz
verified_signature_id uuid
supersedes_id uuid
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 17

### `reconciliation_record`

```text
batch/scope
reconciliation type
item/material/label/component ID
source quantity categories
tolerance rule
variance
outcome
linked quality event
version/status
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ebmr` (Doc 100)
- Source: Document 17


## Document 18 — Procurement & Supplier Quality Specification (SPEC-MAT-001)

**Owner service:** `services/gxp-api/src/modules/materials` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `supplier`

```text
id uuid PK
tenant_id uuid
supplier_code varchar(120)
legal_name varchar(255)
role_type varchar(40)
status varchar(40)
country varchar(80)
external_mappings jsonb
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 18

### `supplier_site`

```text
supplier ID
site identity/address
manufacturer flag
regulatory/certification refs
status
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 18

### `supplier_qualification`

```text
id uuid PK
supplier_site_id uuid
scope jsonb
risk_class varchar(40)
status varchar(40)
effective_from timestamptz
expires_at timestamptz
quality_agreement_vault_id uuid
approval_signatures jsonb
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 18

### `approved_supplier_material`

```text
supplier site
manufacturer site
material specification version
receiving site
approval status
conditional controls
effective dates
test/inspection profile override
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 18

### `purchase_requisition`

```text
material spec
site
need date
source requirements
status/version
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 18

### `purchase_order_ref`

```text
native/external mode
supplier/manufacturer
material spec
revision
regulated requirement snapshot
external system version/sync status
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 18


## Document 19 — Material Receipt, Quarantine & Quality Status Specification (SPEC-MAT-002A)

**Owner service:** `services/gxp-api/src/modules/materials` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `material_receipt`

```text
id uuid PK
tenant_id uuid
site_id uuid
receipt_number varchar(120)
po_reference varchar(160)
supplier_id uuid
manufacturer_id uuid
received_at timestamptz
receiver_subject_id uuid
state varchar(40)
version bigint
shipment_condition_status varchar(40)
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 19

### `material_lot`

```text
id uuid PK
material_spec_version_id uuid
internal_lot_no varchar(160)
supplier_lot_no varchar(200)
manufacturer_lot_no varchar(200)
receipt_id uuid
manufacture_date date
expiry_date date
retest_date date
quality_status varchar(40)
quality_status_version bigint
released_at timestamptz
release_signature_id uuid
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 19

### `material_container`

```text
lot ID
container code/barcode
received/current quantity
current warehouse/location
quality status inheritance/override
sampled flag
seal/damage status
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 19

### `sampling_order`

```text
lot
sampling plan/version
selected containers
sample quantities
assigned sampler
status
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 19

### `material_quality_disposition`

```text
lot/container scope
evidence/test references
decision
signature
effective time
reason/deviation
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 19


## Document 20 — Inventory, Lot/Container & Warehouse Specification (SPEC-MAT-002B)

**Owner service:** `services/gxp-api/src/modules/materials` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `warehouse_location`

```text
id uuid PK
tenant_id uuid
site_id uuid
warehouse_code varchar(100)
location_code varchar(120)
zone_type varchar(50)
status varchar(40)
environment_profile_id uuid
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 20

### `inventory_transaction`

```text
id uuid PK
tenant_id uuid
site_id uuid
material_lot_id uuid
container_id uuid
transaction_type varchar(50)
quantity numeric(24,8)
uom varchar(40)
from_location_id uuid
to_location_id uuid
reference_type varchar(60)
reference_id uuid
source_event_id uuid
occurred_at timestamptz
actor_type varchar(40)
actor_id varchar(255)
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 20

### `inventory_balance_projection`

```text
material lot/container/location
on_hand
reserved
available
projection version
last transaction ID
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 20

### `inventory_reservation`

```text
batch/order
material requirement
lot/container
quantity
status
expiry
version
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 20


## Document 21 — Material Dispensing & Weighing Specification (SPEC-MAT-002C)

**Owner service:** `services/gxp-api/src/modules/materials` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `dispensing_order`

```text
id uuid PK
batch_id uuid
batch_step_id uuid
material_requirement_id uuid
material_spec_version_id uuid
target_rule_id uuid
target_qty numeric(24,8)
target_uom varchar(40)
tolerance_rule_id uuid
state varchar(40)
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 21

### `dispensing_source`

```text
order ID
material lot ID
source container ID
reserved quantity
actual taken quantity
source eligibility evaluation
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 21

### `weighing_session`

```text
order
balance ID
operator
booth/location
tare
readings
stable result
source/manual flag
rule version
start/end
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 21

### `dispensed_container`

```text
new container ID
batch
material
actual quantity
source list
status
label print job
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 21


## Document 22 — Material Consumption, Return, Adjustment, Destruction & Reconciliation Specification (SPEC-MAT-002D)

**Owner service:** `services/gxp-api/src/modules/materials` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `material_consumption`

```text
id uuid PK
batch_id uuid
step_id uuid
dispensed_container_id uuid
material_lot_id uuid
quantity numeric(24,8)
uom varchar(40)
source_type varchar(40)
source_id varchar(255)
occurred_at timestamptz
transaction_id uuid
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 22

### `material_return`

```text
source batch/dispensed container
quantity
container condition
storage/exposure evidence
target location
resulting quality status
transaction ID
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 22

### `inventory_adjustment_request`

```text
scope
expected quantity
observed quantity
variance
reason
evidence
approval/signature
resulting reversal/adjustment transactions
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 22

### `destruction_record`

```text
material/product scope
lot/container
quantity
reason
method
vendor
witnesses
evidence
transaction
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 22

### `material_reconciliation`

```text
batch/material requirement
source quantities
calculation rule/version
outcome
variance
linked deviation
version
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/materials` (Doc 100)
- Source: Document 22


## Document 23 — Native Basic QC & Sampling Specification (SPEC-QC-001)

**Owner service:** `services/gxp-api/src/modules/qc` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `qc_test_specification`

```text
id uuid PK
tenant_id uuid
spec_code varchar(120)
version_no bigint
scope_type varchar(40)
scope_version_id uuid
status varchar(40)
effective_from/to
sampling_plan_id uuid
released_vault_object_id uuid
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qc` (Doc 100)
- Source: Document 23

### `qc_test_definition`

```text
specification
test code/name
method version
result data type
acceptance rule
required flag
review policy
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qc` (Doc 100)
- Source: Document 23

### `qc_sample`

```text
id uuid PK
tenant_id uuid
sample_number varchar(160)
sample_type varchar(50)
source_type varchar(50)
source_id uuid
source_location_ref varchar(200)
lot_batch_serial_ref varchar(200)
sample_quantity numeric(24,8)
sample_uom varchar(40)
sampled_at timestamptz
received_at timestamptz
sampler_subject_id uuid
state varchar(40)
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qc` (Doc 100)
- Source: Document 23

### `qc_test_order`

```text
sample ID
test definition/version
assigned analyst
state/version
started/completed/reviewed times
blocking status
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qc` (Doc 100)
- Source: Document 23

### `qc_test_run`

```text
test order
method version
instrument/equipment ID
analyst
sample amount
reference standards/reagents
system suitability
calculation version
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qc` (Doc 100)
- Source: Document 23

### `qc_result`

```text
id uuid PK
test_order_id uuid
test_run_id uuid
result_version bigint
result_type varchar(40)
value_decimal numeric(30,12)
value_text text
value_json jsonb
uom varchar(40)
acceptance_rule_id uuid
outcome varchar(40)
oos_record_id uuid
oot_record_id uuid
supersedes_result_id uuid
created_at timestamptz
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qc` (Doc 100)
- Source: Document 23


## Document 25 — OOS / OOT Management Specification (SPEC-QC-003)

**Owner service:** `services/gxp-api/src/modules/qc` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `oos_record`

```text
id uuid PK
tenant_id uuid
site_id uuid
oos_number varchar(120)
source_result_id uuid NOT NULL
sample_id uuid
test_order_id uuid
batch_id uuid
material_lot_id uuid
state varchar(50)
severity varchar(40)
version bigint
hold_status varchar(40)
final_classification varchar(60)
root_cause_code varchar(100)
opened_at timestamptz
closed_at timestamptz
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qc` (Doc 100)
- Source: Document 25

### `oos_investigation_activity`

```text
phase/type
checklist/question
response
evidence refs
investigator
timestamp
version
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qc` (Doc 100)
- Source: Document 25

### `oos_retest_plan`

```text
justification
number of retests
method
analyst/instrument criteria
interpretation rule
approver signature
status
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qc` (Doc 100)
- Source: Document 25

### `oos_resample_plan`

```text
scientific rationale
sampling plan/version
source
approver
resulting sample IDs
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qc` (Doc 100)
- Source: Document 25

### `oot_record`

```text
source result
trend rule/version
baseline/reference
trigger details
state
investigation/impact
closure
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qc` (Doc 100)
- Source: Document 25


## Document 26 — Deviation & Investigation Management (SPEC-QMS-001)

**Owner service:** `services/gxp-api/src/modules/qms` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `deviation_record`

```text
id uuid PK
quality_event_id uuid UNIQUE
deviation_number varchar(120) UNIQUE
deviation_type varchar(40)
source_type/source_id/source_version
severity varchar(40)
state varchar(50)
owner_subject_id uuid
investigator_subject_id uuid
planned boolean
planned_scope jsonb
immediate_correction jsonb
containment jsonb
root_cause jsonb
impact_assessment jsonb
disposition_code varchar(80)
due_date timestamptz
version bigint
closed_at timestamptz
```

**Indexes (source):** (tenant_id,state,due_date), (site_id,severity,state).

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 26

### `deviation_impact_link`

```text
impacted record type/ID/version
impact category
hold/disposition reference
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 26


## Document 27 — CAPA Management (SPEC-QMS-002)

**Owner service:** `services/gxp-api/src/modules/qms` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `capa_record`

```text
id uuid PK
quality_event_id uuid UNIQUE
capa_number varchar(120) UNIQUE
problem_statement text
risk_class varchar(40)
root_cause_ref jsonb
state varchar(50)
owner_subject_id uuid
target_date timestamptz
effectiveness_plan jsonb
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 27

### `capa_action`

```text
action type
owner
due date
dependency links
implementation evidence
verification status/signature
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 27

### `capa_effectiveness_check`

```text
criterion
data source
observation period
result
reviewer/signature
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 27


## Document 28 — Nonconformance Management (SPEC-QMS-003)

**Owner service:** `services/gxp-api/src/modules/qms` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `nonconformance_record`

```text
id uuid PK
quality_event_id uuid UNIQUE
ncr_number varchar(120) UNIQUE
scope_type varchar(50)
scope_records jsonb
requirement_ref jsonb
defect_code varchar(100)
severity varchar(40)
state varchar(50)
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 28

### `ncr_disposition`

```text
affected scope subset
quantity/serials
disposition
justification
approver signatures
rework route
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 28


## Document 29 — Change Control (SPEC-QMS-004)

**Owner service:** `services/gxp-api/src/modules/qms` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `change_control`

```text
id uuid PK
quality_event_id uuid UNIQUE
change_number varchar(120) UNIQUE
change_type varchar(50)
classification varchar(40)
current_state jsonb
proposed_state jsonb
state varchar(50)
risk_ref uuid
regulatory_impact jsonb
validation_impact jsonb
training_impact jsonb
effective_at timestamptz
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 29

### `change_affected_object`

```text
object type/ID/version
impact category
action required
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 29

### `change_task`

```text
owner
task/evidence
dependency
due date/status
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 29


## Document 30 — Document Control (SPEC-QMS-005)

**Owner service:** `services/gxp-api/src/modules/qms` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `controlled_document`

```text
id uuid PK
tenant_id uuid
document_code varchar(120) UNIQUE
document_type varchar(60)
owner_subject_id uuid
department_id uuid
site_scope jsonb
status varchar(40)
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 30

### `controlled_document_version`

```text
id uuid PK
document_id uuid
version_label varchar(60)
vault_object_id uuid
content_hash char(64)
state varchar(40)
effective_from timestamptz
effective_to timestamptz
change_control_id uuid
periodic_review_due timestamptz
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 30

### `controlled_copy`

```text
document version
copy number
recipient/location
issued/returned/destroyed status
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 30


## Document 31 — Training & Personnel Qualification (SPEC-QMS-006)

**Owner service:** `services/gxp-api/src/modules/qms` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `training_requirement`

```text
source type/version
role/site/product/equipment scope
training type
recurrence/expiry
assessment requirement
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 31

### `training_assignment`

```text
id uuid PK
subject_id uuid
requirement_id uuid
source_version_id uuid
state varchar(40)
assigned_at timestamptz
due_at timestamptz
completed_at timestamptz
result varchar(40)
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 31

### `qualification_record`

```text
subject
qualification code
scope
effective/expiry
state
evaluator/signature
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 31


## Document 32 — Supplier Quality / SCAR (SPEC-QMS-007)

**Owner service:** `services/gxp-api/src/modules/qms` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `supplier_quality_case`

```text
quality event ID
supplier/manufacturer site
material/spec
affected lots
severity/state
internal owner
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 32

### `scar_record`

```text
case ID
issued/due dates
supplier response
supplier root cause/action
internal review
effectiveness
closure signature
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 32


## Document 33 — Risk Management (SPEC-QMS-008)

**Owner service:** `services/gxp-api/src/modules/qms` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `risk_record`

```text
id uuid PK
quality_event_id uuid
risk_number varchar(120) UNIQUE
risk_type varchar(50)
methodology_id uuid
context jsonb
hazard_problem text
potential_effect text
state varchar(40)
owner_subject_id uuid
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 33

### `risk_assessment_version`

```text
scoring inputs
initial score/class
controls
residual inputs/score
acceptance criteria
approver/signature
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 33


## Document 34 — Internal Audit Management (SPEC-QMS-009)

**Owner service:** `services/gxp-api/src/modules/qms` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `internal_audit`

```text
id uuid PK
quality_event_id uuid
audit_number varchar(120) UNIQUE
program_ref varchar(120)
site_scope jsonb
process_scope jsonb
criteria_refs jsonb
lead_auditor_id uuid
team jsonb
scheduled_at timestamptz
actual_start/end timestamptz
state varchar(40)
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 34

### `audit_finding`

```text
audit ID
finding number
requirement/reference
evidence
classification
owner
response
verification/closure
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 34


## Document 35 — Complaint Management (SPEC-QMS-010)

**Owner service:** `services/gxp-api/src/modules/qms` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `complaint_record`

```text
id uuid PK
quality_event_id uuid UNIQUE
complaint_number varchar(120) UNIQUE
received_at timestamptz
source_channel varchar(40)
product_ref uuid
lot_batch_serial_refs jsonb
complainant_ref/encrypted_fields jsonb
nature_code varchar(100)
description text
constituent_classification varchar(60)
state varchar(50)
investigation_required boolean
no_investigation_reason text
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 35

### `complaint_reportability_assessment`

```text
applicable regime(s)
assessment inputs/rationale
due date
reviewer/signature
submission reference/status
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 35

### `complaint_communication`

```text
direction
recipient/channel
date
approved message/reference
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 35


## Document 36 — Recall / Field Action Management (SPEC-QMS-011)

**Owner service:** `services/gxp-api/src/modules/qms` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `field_action`

```text
id uuid PK
quality_event_id uuid UNIQUE
action_number varchar(120) UNIQUE
action_type varchar(60)
trigger_ref jsonb
state varchar(50)
risk_assessment_ref uuid
reportability_assessment jsonb
scope_snapshot_id uuid
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 36

### `field_action_scope_item`

```text
product/lot/serial/package
distribution reference
status/action required/completed
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 36

### `field_action_communication`

```text
communication version
recipient
sent/delivery/ack status
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 36

### `field_action_reconciliation`

```text
affected/contacted/returned/corrected/destroyed/outstanding
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 36


## Document 37 — Quality Metrics, Trending & Effectiveness Checks (SPEC-QMS-012)

**Owner service:** `services/gxp-api/src/modules/qms` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `quality_metric_definition`

```text
id uuid PK
metric_code varchar(120)
version_no bigint
source_model_id varchar(120)
numerator_definition jsonb
denominator_definition jsonb
formula_rule_id uuid
scope_dimensions jsonb
frequency varchar(40)
threshold_rule_ids jsonb
effective_from/to
state varchar(40)
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 37

### `quality_metric_snapshot`

```text
id uuid PK
metric_definition_id uuid
period_start timestamptz
period_end timestamptz
scope jsonb
source_cutoff timestamptz
result jsonb
formula_version varchar(40)
state varchar(40)
created_at timestamptz
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 37

### `effectiveness_check`

```text
source module/record
criterion
metric/data source
observation period
due date
result/evidence
reviewer/signature
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/qms` (Doc 100)
- Source: Document 37


## Document 38 — Equipment, Calibration, Qualification & Maintenance (SPEC-EQP-001)

**Owner service:** `services/gxp-api/src/modules/equipment` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `equipment_asset`

```text
id uuid PK
tenant_id uuid
site_id uuid
equipment_code varchar(120) UNIQUE
equipment_class_id uuid
manufacturer varchar(255)
model varchar(160)
serial_no varchar(160)
location_id uuid
state varchar(50)
qualification_status varchar(40)
calibration_status varchar(40)
maintenance_status varchar(40)
cleanliness_status varchar(40)
firmware_version varchar(80)
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 38

### `equipment_calibration`

```text
asset ID
calibration plan/version
due/performed dates
adjustments
standards used
result/status
impact assessment/deviation
performer/reviewer signatures
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 38

### `maintenance_work_order`

```text
type planned/corrective
fault/diagnosis
work/parts
technician
verification
state/version
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 38

### `equipment_use_log`

```text
equipment
batch/product/step
start/end
operator/source
cleaning context
event references
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 38


## Document 39 — Cleaning, Sanitization & Line Clearance (SPEC-EQP-002)

**Owner service:** `services/gxp-api/src/modules/equipment` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `cleaning_procedure_version`

```text
equipment/area scope
cleaning type
agents/concentrations
steps/times
disassembly
sample/inspection requirements
dirty/clean hold limits
validation reference
released Vault ID
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 39

### `cleaning_execution`

```text
id uuid PK
equipment_id/area_id uuid
procedure_version_id uuid
batch_context jsonb
state varchar(40)
started_at/completed_at timestamptz
dirty_since timestamptz
clean_until timestamptz
agents_used jsonb
performer/reviewer jsonb
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 39

### `line_clearance`

```text
line/area
previous batch/product
next batch/product
checklist version
material/label/equipment items
performer/verifier
state/expiry
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 39


## Document 40 — Sterile / Aseptic Manufacturing Operations (SPEC-EQP-003)

**Owner service:** `services/gxp-api/src/modules/equipment` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `aseptic_profile_version`

```text
product/recipe scope
required area class/profile
personnel qualifications
sterile input requirements
intervention catalogue
filter/sterilization requirements
release blockers
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 40

### `aseptic_operation`

```text
id uuid PK
batch_id uuid
recipe_stage_id uuid
area_id uuid
profile_version_id uuid
state varchar(40)
started_at/completed_at timestamptz
environment_snapshot_ref uuid
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 40

### `aseptic_intervention`

```text
operation ID
intervention type/version
planned/unplanned
operator
start/end
location
reason
impacted time/unit scope
deviation/impact link
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 40

### `aseptic_event_timeline`

```text
event type
source
authoritative timestamp
batch/operation scope
severity
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 40


## Document 41 — Environmental Monitoring & Cleanroom State Control (SPEC-EQP-004)

**Owner service:** `services/gxp-api/src/modules/equipment` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `em_program_version`

```text
site/area scope
monitoring types
locations
method/version
frequency
alert/action limits
operation/shift coverage
review/trend rules
released Vault ID
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 41

### `em_location`

```text
area/room/zone
location code
criticality
sample types
active/effective status
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 41

### `em_sample_or_reading`

```text
id uuid PK
program_version_id uuid
location_id uuid
monitoring_type varchar(60)
batch_id/aseptic_operation_id uuid
instrument_or_media_ref jsonb
sampled_at/acquired_at timestamptz
result jsonb
alert_action_status varchar(40)
review_state varchar(40)
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 41

### `em_excursion`

```text
source result/event
affected area/time/batches
organism/details
disposition
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 41


## Document 42 — Sterilization, CIP/SIP & Sterile Filtration Management (SPEC-EQP-005)

**Owner service:** `services/gxp-api/src/modules/equipment` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `process_cycle_profile_version`

```text
process type
equipment class
load pattern
controller recipe/version
critical parameters/limits
indicator requirements
review policy
validation reference
released Vault ID
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 42

### `process_cycle`

```text
id uuid PK
process_type varchar(40)
equipment_id uuid
profile_version_id uuid
batch_id uuid
controller_cycle_id varchar(160)
load_id uuid
state varchar(40)
started_at/completed_at timestamptz
parameter_summary jsonb
alarm_summary jsonb
raw_evidence_ref uuid
review_signature_id uuid
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 42

### `sterilization_load_item`

```text
cycle/load
item/equipment/component/lot/container
position/load pattern
resulting sterile status/expiry
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 42

### `sterile_filter_use`

```text
filter lot/serial
batch/process
installation
pre/post integrity test refs
process parameters
state
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/equipment` (Doc 100)
- Source: Document 42


## Document 54 — Prefilled Syringe & Injectable DDCP Manufacturing Profile (SPEC-DDCP-001)

**Owner service:** `services/gxp-api/src/modules/ddcp` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `ddcp_profile_version`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ddcp` (Doc 100)
- Source: Document 54

### `constituent_requirement`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ddcp` (Doc 100)
- Source: Document 54

### `constituent_handoff`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ddcp` (Doc 100)
- Source: Document 54

### `fill_operation`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ddcp` (Doc 100)
- Source: Document 54

### `production_count_ledger`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ddcp` (Doc 100)
- Source: Document 54

### `device_assembly_record`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ddcp` (Doc 100)
- Source: Document 54

### `device_functional_test_link`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ddcp` (Doc 100)
- Source: Document 54

### `ddcp_release_checkpoint`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ddcp` (Doc 100)
- Source: Document 54

### `batch_evidence_manifest`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/ddcp` (Doc 100)
- Source: Document 54


## Document 58 — Postmarket Surveillance, Safety Case & Signal Management (SPEC-PM-001)

**Owner service:** `services/gxp-api/src/modules/postmarket` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `postmarket_source`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/postmarket` (Doc 100)
- Source: Document 58

### `safety_case`

```text
id uuid PK
safety_case_number varchar UNIQUE
source_record_type/id/version
source_receipt_at timestamptz
company_initial_receipt_at timestamptz
regulatory_clock_candidate_at timestamptz
system_ingested_at timestamptz
marketed_product_id uuid
application_profile_id uuid
constituent_classification jsonb
state varchar
current_classification_version bigint
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/postmarket` (Doc 100)
- Source: Document 58

### `safety_case_followup`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/postmarket` (Doc 100)
- Source: Document 58

### `safety_signal`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/postmarket` (Doc 100)
- Source: Document 58


## Document 59 — Regulatory Reportability Assessment & Electronic Safety Submission Management (SPEC-PM-002)

**Owner service:** `services/gxp-api/src/modules/postmarket` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `reportability_track`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/postmarket` (Doc 100)
- Source: Document 59

### `regulatory_report`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/postmarket` (Doc 100)
- Source: Document 59

### `regulatory_submission_attempt`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/postmarket` (Doc 100)
- Source: Document 59

### `regulatory_submission_ack`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/postmarket` (Doc 100)
- Source: Document 59


## Document 60 — Combination-Product Postmarket Regulatory Coordination, Information Sharing & Regulatory Calendar (SPEC-PM-003)

**Owner service:** `services/gxp-api/src/modules/postmarket` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `regulatory_obligation`

```text
id uuid PK
obligation_type varchar
source_type/id/version
application_id uuid
rule_version_id uuid
clock_start_at timestamptz
original_due_at timestamptz
current_due_at timestamptz
calendar_profile_id uuid
state varchar
owner_subject_id uuid
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/postmarket` (Doc 100)
- Source: Document 60

### `applicant_relationship`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/postmarket` (Doc 100)
- Source: Document 60

### `constituent_information_share`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/postmarket` (Doc 100)
- Source: Document 60

### `correction_removal_regulatory_record`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/postmarket` (Doc 100)
- Source: Document 60

### `periodic_reporting_cycle`

`SCHEMA NOT SPECIFIED IN SOURCE` — entity named without column/type/constraint definition.

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `services/gxp-api/src/modules/postmarket` (Doc 100)
- Source: Document 60


## Document 61 — Security Architecture, Threat Model & Control Framework (SPEC-SEC-001)

**Owner service:** `platform/security` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `security_threat_model_version`

```text
id uuid PK
system_version varchar
methodology_version varchar
deployment_profile varchar
state varchar
vault_ref uuid
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 61

### `security_threat`

```text
threat model version
asset/boundary
attack preconditions
impacted CIA/GxP attributes
inherent/residual risk
state
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 61

### `security_control`

```text
control code
objective
implementation owner
evidence source
test owner
framework mappings
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 61

### `security_exception`

```text
control/requirement
risk assessment
compensating controls
effective/expiry
approvers
remediation target
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 61


## Document 62 — Identity Federation, SSO, MFA, Sessions & Service Identities (SPEC-SEC-002)

**Owner service:** `platform/security` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `identity_provider_config`

```text
tenant/deployment
issuer/entity ID
protocol OIDC/SAML
trust/signing keys metadata
claim mapping version
state/effective dates
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 62

### `application_session`

```text
id uuid PK
subject_id uuid
tenant_id uuid
auth_time timestamptz
auth_strength jsonb
created_at/expires_at/idle_expires_at
state varchar
revoked_reason
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 62

### `service_identity`

```text
service/client ID
tenant/site scope
allowed audiences/scopes
auth method
certificate/key refs
lifecycle status
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 62


## Document 63 — Privileged Access, Support Access, Break-Glass & Administrative Security (SPEC-SEC-003)

**Owner service:** `platform/security` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `privileged_access_request`

```text
id uuid PK
subject_id uuid
requested_role varchar
tenant/site/resource_scope jsonb
reason text
ticket_ref varchar
requested_start/end
state varchar
approver_id uuid
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 63

### `privileged_grant`

```text
request ID
role/scope
effective/expiry
auth strength
state
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 63

### `privileged_session`

```text
grant
start/end
connection/source
actions/command refs
recording/evidence ref
review status
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 63


## Document 64 — Application, API, UI & Secure Runtime Engineering (SPEC-SEC-004)

**Owner service:** `platform/security` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `api_security_policy`

```text
auth mode
allowed roles/scopes
object policy
writable/readable field sets
rate/resource limits
file/export policy
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 64

### `outbound_destination`

```text
service ID
schemes/hosts/ports
redirect policy
auth/secret ref
purpose/state
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 64

### `webhook_profile`

```text
provider
auth mechanism
replay window
schema version
size limits
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 64


## Document 65 — Secrets Management, PKI, Cryptography & Key Lifecycle (SPEC-SEC-005)

**Owner service:** `platform/security` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `secret_metadata`

```text
secret ID/reference
provider
purpose/owner
consumer identities
version
rotation interval
last/next rotation
state
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 65

### `certificate_metadata`

```text
id uuid PK
serial varchar UNIQUE
subject/sans jsonb
identity_id uuid
profile varchar
issued_at/expires_at
state varchar
issuer_ref
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 65

### `crypto_profile`

```text
hash algorithms
symmetric/asymmetric algorithms
key sizes
effective dates
migration notes
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 65


## Document 66 — Network, Tenant, Deployment Isolation & Zero-Trust Architecture (SPEC-SEC-006)

**Owner service:** `platform/security` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `network_flow_definition`

```text
source zone/service
destination zone/service
protocol/port
purpose
auth mechanism
deployment profile
effective dates
owner
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 66

### `deployment_security_profile`

```text
ingress/egress policy
private endpoints
namespaces
service accounts
container hardening
admin access pattern
backup/network isolation
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 66


## Document 67 — Security Logging, Monitoring, Incident Response & Forensic Evidence (SPEC-SEC-007)

**Owner service:** `platform/security` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `security_incident`

```text
id uuid PK
incident_number varchar UNIQUE
severity varchar
state varchar
owner_subject_id uuid
affected_scope jsonb
detected_at/contained_at/recovered_at/closed_at
gxp_impact_state varchar
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 67

### `forensic_evidence`

```text
incident
source
acquisition timestamp/actor
hash/algorithm
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 67


## Document 68 — Secure SDLC, Software Supply Chain, SBOM, Vulnerability & Release Security (SPEC-SEC-008)

**Owner service:** `platform/security` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `software_component_inventory`

```text
component/package/image
version/digest
license
source
owner
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 68

### `vulnerability_record`

```text
id uuid PK
vulnerability_id varchar
source varchar
component/version jsonb
affected_releases jsonb
severity varchar
kev_status boolean
gxp_impact jsonb
state varchar
remediation_due timestamptz
version bigint
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 68

### `release_security_evidence`

```text
release/commit
build provenance
scan reports
pen/security test refs
exceptions
gate result
signature/artifact digest
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `platform/security` (Doc 100)
- Source: Document 68


## Document 69 — Enterprise Data Ownership, Persistence Topology & Data Lineage (SPEC-DATA-001)

**Owner service:** `infrastructure` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `data_ownership_registry`

```text
entity_type varchar PK
authoritative_service varchar
authoritative_store POSTGRES|MARIADB|OBJECT|EXTERNAL
projection_targets jsonb
tenant_scoped boolean
site_scoped boolean
classification varchar
retention_policy_id uuid
encryption_profile_id uuid
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `infrastructure` (Doc 100)
- Source: Document 69

### `projection_checkpoint`

```text
projection type
source stream/entity
last source event/version
projected_at
state/error
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `infrastructure` (Doc 100)
- Source: Document 69

### `migration_batch`

```text
source system/artifact
source hash
transform version
start/end
counts/hash reconciliation
approver/evidence
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `infrastructure` (Doc 100)
- Source: Document 69


## Document 72 — Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle (SPEC-DATA-004)

**Owner service:** `infrastructure` | **Authoritative store:** Object store (WORM evidence) + PostgreSQL metadata

### `evidence_object`

```text
id uuid PK
tenant_id uuid
owner_type/id/version
provider varchar
bucket/container varchar
object_key varchar
provider_version_id varchar
size_bytes bigint
mime_type varchar
hash_algorithm varchar
content_hash varchar
state varchar
retention_policy_id uuid
retention_until timestamptz
legal_hold boolean
created_at timestamptz
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `infrastructure` (Doc 100)
- Source: Document 72

### `evidence_manifest`

```text
owner record/version
manifest type/version
ordered evidence items
canonical hash
renderer/export version if applicable
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `infrastructure` (Doc 100)
- Source: Document 72


## Document 73 — NATS / JetStream Event Bus, Transactional Outbox & Async Contracts (SPEC-DATA-005)

**Owner service:** `infrastructure` | **Authoritative store:** PostgreSQL transactional outbox (authoritative) / NATS JetStream (transport)

### `gxp_outbox`

```text
event_id uuid PK
aggregate_type/id/version
event_type/schema_version
tenant_id/site_id
payload jsonb
correlation_id/causation_id
occurred_at
publish_state
attempt_count
next_attempt_at
published_at
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `infrastructure` (Doc 100)
- Source: Document 73

### `consumer_inbox`

```text
consumer_name
event_id
payload_hash
processed_at
result_ref
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `infrastructure` (Doc 100)
- Source: Document 73


## Document 75 — Caching, Search, Read Models, Reporting Projections & Analytics Data Access (SPEC-DATA-007)

**Owner service:** `infrastructure` | **Authoritative store:** Redis / search / read models (rebuildable, NON-AUTHORITATIVE)

### `projection_document_metadata`

```text
source type/id/version
tenant/site
projected_at
schema version
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `infrastructure` (Doc 100)
- Source: Document 75

### `read_model_checkpoint`

```text
model
source stream/table
last event/version/cutoff
state/error
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `infrastructure` (Doc 100)
- Source: Document 75


## Document 76 — Backup, Restore, Point-in-Time Recovery & Disaster Recovery (SPEC-DATA-008)

**Owner service:** `infrastructure` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `recovery_objective_profile`

```text
business capability/component
backup frequency
secondary region/site requirements
owner/approver
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `infrastructure` (Doc 100)
- Source: Document 76

### `backup_inventory`

```text
component
backup ID/type
start/end
source version/timeline
size/hash/manifest
encryption/key ref
storage location
retention
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `infrastructure` (Doc 100)
- Source: Document 76

### `restore_test`

```text
backup set
target
elapsed time
integrity checks
evidence/report
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `infrastructure` (Doc 100)
- Source: Document 76


## Document 77 — Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade Architecture (SPEC-DATA-009)

**Owner service:** `infrastructure` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `deployment_profile`

```text
provider/environment/customer
release versions
region/site topology
service sizing
network/security profile
storage classes
external endpoints
certificate/secret profiles
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `infrastructure` (Doc 100)
- Source: Document 77


## Document 78 — Performance, Capacity, Observability, SLOs & SRE Operations (SPEC-DATA-010)

**Owner service:** `infrastructure` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `slo_definition`

```text
capability
target
evaluation window
deployment profile
error budget/alert rules
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `infrastructure` (Doc 100)
- Source: Document 78

### `capacity_forecast`

```text
component/resource
current usage
growth assumptions
forecast horizon
required headroom
threshold/date
recommended action
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `infrastructure` (Doc 100)
- Source: Document 78


## Document 79 — Validation Master Plan & Computer Software Assurance Strategy (SPEC-VAL-001)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `validation_master_plan`

```text
scope
regulatory profiles
methodology
deliverable rules
responsibilities
approval/version.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 79

### `validation_deliverable_requirement`

```text
artifact type
risk condition
owner
review/signature
evidence type
release-blocker flag.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 79

### `validation_release_gate`

```text
release/config/environment scope
required artefacts
blockers
decision refs.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 79


## Document 80 — Intended Use, GxP Criticality & Software Function Risk Classification (SPEC-VAL-002)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `intended_use`

```text
scope/version
regulated process
users
record/signature relevance.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 80

### `function_risk_assessment`

```text
function/version
failure modes
impacts
detectability
automation role
controls
category
assurance level
approval.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 80


## Document 81 — Requirements, Design Inputs & Validation Traceability Management (SPEC-VAL-003)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `validation_requirement`

```text
stable code
source doc/version/section
text
class
regulatory source
current version.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 81

### `trace_link`

```text
source artifact/version → target artifact/version + relation type.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 81

### `requirement_baseline`

```text
release/customer scope
requirement version list
exclusions/rationale
hash/Vault ref.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 81


## Document 82 — Validation Test Strategy, Test Methods & Objective Evidence Governance (SPEC-VAL-004)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `validation_test_definition`

```text
code/version
method
requirement/risk links
preconditions/data
procedure/charter
expected results
review rule.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 82

### `validation_test_execution`

```text
exact test/environment
tester/CI
observations
final status
evidence manifest
defect/deviation links.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 82


## Document 83 — Installation Qualification (IQ) & Installed Baseline Verification (SPEC-VAL-005)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `iq_protocol`

```text
environment/release/profile
expected components/checks/acceptance.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 83

### `iq_execution`

```text
installed inventory fingerprint
check results
deviations
evidence manifest
approval.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 83


## Document 84 — Operational Qualification (OQ) & Functional Control Verification (SPEC-VAL-006)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `oq_suite`

```text
baseline
selected tests/evidence
exclusions/rationale
environment fingerprint.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 84

### `oq_execution`

```text
suite version
test refs
coverage
deviations
approval.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 84


## Document 85 — Performance Qualification (PQ), UAT & Business Process Verification (SPEC-VAL-007)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `pq_scenario`

```text
site/profile/process
roles/training
prerequisites
steps
interfaces/equipment
acceptance.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 85

### `pq_execution`

```text
participant identities
environment/config
observations/results/evidence/deviations/approval.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 85


## Document 86 — Infrastructure, Cloud, Platform & Environment Qualification (SPEC-VAL-008)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `infrastructure_qualification_profile`

```text
deployment/provider
required components/config ranges
control tests
supplier evidence
change triggers.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 86

### `infrastructure_fingerprint`

```text
versions
config hashes
resources
network/security/time/backup refs.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 86


## Document 87 — Data Migration, Conversion, Cutover & Reconciliation Validation (SPEC-VAL-009)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `migration_validation_plan`

```text
source/target
scope
cutoff
mappings
transform version
reconciliation rules
acceptance.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 87

### `migration_run`

```text
source hash
scripts/config
counts
errors
target refs.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 87

### `migration_reconciliation`

```text
counts/hashes/totals/critical-field comparisons/files/deviations.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 87


## Document 88 — 21 CFR Part 11 Electronic Records & Electronic Signature Validation (SPEC-VAL-010)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `part11_scope_assessment`

```text
record/signature type
predicate use
system component
closed/open context
applicability
customer responsibilities.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 88

### `part11_control_evidence`

```text
control/citation
test/result/evidence
config
procedure
deviation.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 88


## Document 89 — Audit Trail, Record Version Vault & Data Integrity Validation (SPEC-VAL-011)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `data_integrity_test_profile`

```text
data class
lifecycle
threats
controls
tests.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 89

### `tamper_test_execution`

```text
isolated snapshot
tamper action
verifier version
detection evidence.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 89


## Document 90 — Integration, Edge, Device, Peripheral & Interface Validation (SPEC-VAL-012)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `interface_validation_profile`

```text
provider/device
contract/mapping versions
intended use/risk
auth/source/time/quality expectations
failure scenarios.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 90

### `interface_test_execution`

```text
inputs/raw payloads
canonical outputs
GxP results
external reconciliation.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 90


## Document 91 — Backup, Restore, PITR & Disaster Recovery Qualification (SPEC-VAL-013)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `dr_qualification_scenario`

```text
failure type
components
recovery method
target RPO/RTO
restore order
acceptance.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 91

### `dr_qualification_execution`

```text
backup set
restore point/timeline
actual objectives
integrity/smoke results
deviations.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 91


## Document 92 — Security Qualification, Vulnerability Verification & Penetration Testing (SPEC-VAL-014)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `security_qualification_suite`

```text
release/deployment
threat/control baseline
tests.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 92

### `security_qualification_finding`

```text
source
control
severity
affected release
vulnerability/change/deviation
retest/exception.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 92


## Document 93 — Performance, Load, Capacity & Reliability Qualification (SPEC-VAL-015)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `performance_qualification_scenario`

```text
release/environment
user/process load
data cardinality
duration
failures
thresholds.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 93

### `performance_run`

```text
build/config
harness
metrics/traces/errors/resources
headroom/bottleneck.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 93


## Document 94 — Validation Defect, Deviation, Test Exception & Remediation Management (SPEC-VAL-016)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `validation_exception`

```text
type
source execution
affected requirements
severity/GxP/release impact
state/disposition
cause
issue/change refs
retest plan
version.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 94


## Document 95 — Validation Summary Report, Release-to-Production & Go-Live Authorization (SPEC-VAL-017)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `validation_summary_report`

```text
scope
baselines
evidence refs
deviations
limitations
recommendation
signatures/Vault.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 95

### `validated_release_authorization`

```text
VSR
artifact digests
schema/migrations
config fingerprint
environment/site
state.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 95


## Document 96 — Periodic Review, Change Impact, Revalidation & Validated-State Maintenance (SPEC-VAL-018)

**Owner service:** `validation` | **Authoritative store:** PostgreSQL (GxP Core, authoritative)

### `validated_state_baseline`

```text
release/config/environment/VSR/component inventory/state.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 96

### `validation_change_impact`

```text
change
affected trace artifacts
proposed revalidation level
rationale.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 96

### `periodic_validation_review`

```text
period
changes/incidents/security/DR/performance/access/vendor inputs
findings/actions/decision.
```

- Tenant scope: `tenant_id` required on every regulated table (Doc 70 aggregate baseline)
- Versioning: `version bigint` optimistic concurrency (Doc 70 / MUT-FR-009)
- Immutability: history is superseding, never in-place edited (Doc 06 / Doc 05)
- Retention / legal hold: per record class — **numeric periods unresolved (SG-005)**
- Projection targets: Frappe read models per Doc 71 (non-authoritative)
- Migration owner: `validation` (Doc 100)
- Source: Document 96


## Entities requiring schema completion before migration

| Document | Entity | Action |
|---|---|---|
| 06 | `vault_object` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 06 | `vault_evidence_manifest` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 07 | `iam_qualification` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 54 | `ddcp_profile_version` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 54 | `constituent_requirement` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 54 | `constituent_handoff` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 54 | `fill_operation` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 54 | `production_count_ledger` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 54 | `device_assembly_record` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 54 | `device_functional_test_link` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 54 | `ddcp_release_checkpoint` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 54 | `batch_evidence_manifest` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 58 | `postmarket_source` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 58 | `safety_case_followup` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 58 | `safety_signal` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 59 | `reportability_track` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 59 | `regulatory_report` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 59 | `regulatory_submission_attempt` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 59 | `regulatory_submission_ack` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 60 | `applicant_relationship` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 60 | `constituent_information_share` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 60 | `correction_removal_regulatory_record` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
| 60 | `periodic_reporting_cycle` | Define columns/types/constraints/indexes; register in 36_DATABASE_MIGRATION_CATALOGUE.md |
