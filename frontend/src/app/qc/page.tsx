"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, hasPermission, newIdempotencyKey, pagedFetcher } from "@/lib/api";
import { useApiResource, useEntityOptions, useMe, useSiteId, type EntityOption, type EntityOptionsStatus } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { UomSelect } from "@/components/ui/UomSelect";
import { Icon } from "@/components/ui/Icon";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { useCommand } from "@/components/shared/RecordDetailShell";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { ProductVersionPickerField } from "@/components/shared/ProductVersionPicker";
import { RecipeVersionPickerField } from "@/components/shared/RecipeVersionPicker";
import { SignedJsonForm } from "@/components/shared/SignedJsonForm";
import { RepeatableRows, buildRepeatArray, type RepeatRow, type RepeatSubField } from "@/components/shared/RepeatableFields";

interface Specification {
  id: string;
  spec_code: string;
  version_no: number;
  status: string;
  scope_type: string;
}

interface Sample {
  id: string;
  sample_number: string;
  sample_type: string;
  source_type: string;
  state: string;
}

interface QcMethodVersion {
  method_version_id: string;
  method_code: string;
  version_no: number;
  name: string;
  method_type: string;
  lifecycle_state: string;
}

const SAMPLE_TYPES = ["release", "stability", "in_process", "environmental", "raw_material", "retain"];
// "batch_step" matches SOURCE_TABLE_BY_TYPE["batch_step"] (qc/commands.py) -- required so a sample's
// completion-gating result can actually be found by batch_execution's own per-step check
// (get_passed_qc_spec_ids_for_step joins QcSample.source_type=="batch_step" AND source_id==<step id>;
// a "batch"-sourced sample, however correct-looking, never satisfies it). Was missing entirely before,
// so no UI path could ever produce a step-completing QC result — see SG-220.
const SOURCE_TYPES = ["batch", "batch_step", "material_lot", "environment", "stability_study", "equipment"];
const SCOPE_TYPES = ["product", "in_process", "device"];
const QC_METHOD_TYPES = ["compendial", "internal", "validated"];

// GET /rules/v1 — released rules, flat array (same shape recipe-master's own ruleOptions already reads).
interface ReleasedRuleOption {
  rule_id: string;
  rule_type: string;
  semantic_version: string;
}

function useReleasedRuleOptions(): { options: EntityOption[]; status: EntityOptionsStatus } {
  const { data, error } = useApiResource<ReleasedRuleOption[]>("/rules/v1");
  if (error) return { options: [], status: "error" };
  if (data === null) return { options: [], status: "loading" };
  return {
    options: data.map((r) => ({ value: r.rule_id, label: `${r.rule_id} - ${r.rule_type} v${r.semantic_version}` })),
    status: data.length ? "ready" : "empty",
  };
}

function testDefinitionSubfields(
  uomOptions: EntityOption[],
  uomOptionsStatus: EntityOptionsStatus,
  ruleOptions: EntityOption[],
  ruleOptionsStatus: EntityOptionsStatus
): RepeatSubField[] {
  return [
    { name: "test_code", label: "Test code", required: true, placeholder: "e.g. FILL-WEIGHT" },
    { name: "test_name", label: "Test name", required: true, placeholder: "e.g. Fill weight" },
    { name: "result_data_type", label: "Result data type", required: true, placeholder: "numeric / text / pass_fail / json" },
    // Client requirements #2/#3: the released rules.gxp_uom list, not free text.
    { name: "uom", label: "Unit of measure", type: "customSelect", options: uomOptions, optionsStatus: uomOptionsStatus, optionsNoun: "unit" },
    // Was entirely missing (SG-221): qc/commands.py::_evaluate_acceptance() needs a released rule's
    // business id here to ever compute outcome "pass"/"oos" instead of leaving every recorded result
    // stuck at the "pending" default forever, with no other path (review/correction) ever setting it.
    {
      name: "acceptance_rule_business_id", label: "Acceptance rule", type: "customSelect",
      options: ruleOptions, optionsStatus: ruleOptionsStatus, optionsNoun: "rule",
    },
    {
      name: "trend_rule_business_id", label: "Trend rule (optional)", type: "customSelect",
      options: ruleOptions, optionsStatus: ruleOptionsStatus, optionsNoun: "rule",
    },
    { name: "required", label: "Required", type: "bool", default: "true" },
    { name: "release_blocking", label: "Release blocking", type: "bool", default: "true" },
  ];
}

/** Client requirements #2/#3 -- released UOM codes for the test-definition editor's "customSelect"
 * unit-of-measure field. `/rules/v1/uom` returns a flat array, not a paginated envelope, so this fetches
 * directly rather than through `useListEntityOptions`/`listAll` (both assume pagination). */
function useUomOptions(): { options: EntityOption[]; status: EntityOptionsStatus } {
  const { data, error } = useApiResource<{ code: string }[]>("/rules/v1/uom");
  if (error) return { options: [], status: "error" };
  if (data === null) return { options: [], status: "loading" };
  return { options: data.map((u) => ({ value: u.code, label: u.code })), status: data.length ? "ready" : "empty" };
}

export default function QcPage() {
  const router = useRouter();
  const [createSampleOpen, setCreateSampleOpen] = useState(false);
  const [newSpecOpen, setNewSpecOpen] = useState(false);
  const [newMethodOpen, setNewMethodOpen] = useState(false);
  const [specsReloadToken, setSpecsReloadToken] = useState(0);
  const [samplesReloadToken, setSamplesReloadToken] = useState(0);
  const [methodsReloadToken, setMethodsReloadToken] = useState(0);

  const { me } = useMe();
  // qc_sample.create/.receive, qc_test_order.create/.start/.record_raw_data/.complete share one grant.
  const canAnalyse = hasPermission(me, "qc_test_order.start");

  return (
    <div>
      <PageHead
        title="QC testing"
        subtitle="Samples, test orders, results, second-person review and OOS investigation."
        action={
          <div className="flex gap-2">
            {canAnalyse && (
              <Button variant="secondary" onClick={() => setNewSpecOpen(true)}>
                <Icon name="plus" /> New test specification
              </Button>
            )}
            {canAnalyse && (
              <Button variant="secondary" onClick={() => setNewMethodOpen(true)}>
                <Icon name="plus" /> New method draft
              </Button>
            )}
            {canAnalyse && (
              <Button variant="primary" onClick={() => setCreateSampleOpen(true)}>
                <Icon name="plus" /> New sample
              </Button>
            )}
          </div>
        }
      />

      <Card pad className="mb-4">
        <CardHeader title="Test specifications" />
        <DataTable<Specification>
          columns={specificationColumns}
          fetchPage={pagedFetcher<Specification>("/qc/v1/specifications")}
          rowKey={(s) => s.id}
          searchPlaceholder="Search spec code…"
          emptyIcon="flask"
          emptyMessage='No test specifications yet - use "New test specification" above to add one.'
          defaultSort={{ by: "created_at", dir: "desc" }}
          reloadToken={specsReloadToken}
          onRowClick={(s) => router.push(`/qc/specifications/${s.id}`)}
        />
      </Card>

      <Card pad className="mb-4">
        <CardHeader title="Samples" />
        <DataTable<Sample>
          columns={sampleColumns}
          fetchPage={pagedFetcher<Sample>("/qc/v1/samples")}
          rowKey={(s) => s.id}
          searchPlaceholder="Search sample number…"
          emptyIcon="flask"
          emptyMessage='No samples yet - use "New sample" above to add one.'
          defaultSort={{ by: "created_at", dir: "desc" }}
          reloadToken={samplesReloadToken}
          onRowClick={(s) => router.push(`/qc/samples/${s.id}`)}
        />
      </Card>

      <Card pad className="mb-4">
        <CardHeader title="QC method master" />
        <DataTable<QcMethodVersion>
          columns={methodColumns}
          fetchPage={pagedFetcher<QcMethodVersion>("/qc/v1/methods")}
          rowKey={(m) => m.method_version_id}
          searchPlaceholder="Search method code…"
          emptyIcon="flask"
          emptyMessage='No QC methods yet - use "New method draft" above to add one.'
          defaultSort={{ by: "created_at", dir: "desc" }}
          reloadToken={methodsReloadToken}
          onRowClick={(m) => router.push(`/qc/methods/${m.method_version_id}`)}
        />
      </Card>

      <SignedJsonForm
        title="QC result correction - signed"
        subtitle="Requesting a correction and approving it are independent signatures - the approver must differ from whoever requested the correction (SoD)."
        root="/qc/v1"
        ops={[
          {
            postPath: "results/{result_id}/correct",
            challengePath: "results/{result_id}/signature-challenges",
            action: "correct_request",
            label: "Request a result correction",
            fields: [
              { name: "result_id", label: "QC result ID", required: true },
              { name: "reason_text", label: "Reason", type: "textarea", required: true },
              { name: "corrected_value_decimal", label: "Corrected value (numeric)", hint: "Fill exactly one of the three corrected-value fields, matching the result's data type." },
              { name: "corrected_value_text", label: "Corrected value (text)" },
              { name: "corrected_value_json", label: "Corrected value (structured)", type: "kv" },
            ],
          },
          {
            postPath: "corrections/{correction_id}/approve",
            challengePath: "results/{result_id}/signature-challenges",
            action: "correct_approve",
            label: "Approve a result correction",
            about: "The signature challenge is requested against the original QC result, not the correction record - both IDs are needed below.",
            fields: [{ name: "correction_id", label: "Correction ID", required: true }],
          },
        ]}
      />

      {createSampleOpen && (
        <CreateSampleModal
          onClose={() => setCreateSampleOpen(false)}
          onDone={(id) => {
            setCreateSampleOpen(false);
            setSamplesReloadToken((n) => n + 1);
            router.push(`/qc/samples/${id}`);
          }}
        />
      )}
      {newSpecOpen && (
        <NewSpecificationModal
          onClose={() => setNewSpecOpen(false)}
          onDone={() => {
            setNewSpecOpen(false);
            setSpecsReloadToken((n) => n + 1);
          }}
        />
      )}
      {newMethodOpen && (
        <NewQcMethodDraftModal
          onClose={() => setNewMethodOpen(false)}
          onDone={() => {
            setNewMethodOpen(false);
            setMethodsReloadToken((n) => n + 1);
          }}
        />
      )}
    </div>
  );
}

/** Browsable list for /qc's own "Test specifications" section — previously no way to see what
 * specifications/definitions existed at all, only author one blind via a direct API call. Row click now
 * opens /qc/specifications/[id] (release lives there, not inline). */
const specificationColumns: DataTableColumn<Specification>[] = [
  {
    key: "spec_code",
    header: "Spec code",
    sortable: true,
    render: (s) => (
      <span className="fs-2 font-semibold">
        {s.spec_code} v{s.version_no}
      </span>
    ),
  },
  { key: "scope_type", header: "Scope", render: (s) => <span className="fs-2">{s.scope_type}</span> },
  { key: "status", header: "State", render: (s) => <WorkflowStatePill state={s.status} /> },
];

/** Browsable list for /qc's own "Samples" section — row click now opens /qc/samples/[id] (a real routed
 * detail page, replacing the previous inline giant Modal). */
const sampleColumns: DataTableColumn<Sample>[] = [
  { key: "sample_number", header: "Sample number", sortable: true, render: (s) => <span className="fs-2 font-semibold">{s.sample_number}</span> },
  { key: "sample_type", header: "Sample type", render: (s) => <span className="fs-2">{s.sample_type}</span> },
  { key: "source_type", header: "Source type", render: (s) => <span className="fs-2">{s.source_type}</span> },
  { key: "state", header: "State", render: (s) => <WorkflowStatePill state={s.state} /> },
];

/** Browsable list for /qc's own "QC method master" section — was previously a deliberate code-lookup
 * console (no GET /qc/v1/methods list-all endpoint existed). Now a real list; row click opens
 * /qc/methods/[id]. */
const methodColumns: DataTableColumn<QcMethodVersion>[] = [
  {
    key: "method_code",
    header: "Method code",
    sortable: true,
    render: (m) => (
      <span className="fs-2 font-semibold">
        {m.method_code} v{m.version_no}
      </span>
    ),
  },
  { key: "name", header: "Name", render: (m) => <span className="fs-2">{m.name}</span> },
  { key: "method_type", header: "Type", render: (m) => <span className="fs-2">{m.method_type}</span> },
  { key: "lifecycle_state", header: "State", render: (m) => <WorkflowStatePill state={m.lifecycle_state} /> },
];

/** Two dependent dropdowns — Batch, then that batch's steps — for `source_type=batch_step`. There's no
 * flat "all steps across all batches" list to reuse via useEntityOptions (recipe_step_code isn't unique
 * across batches, e.g. "STEP-A" appears in many), so this reads the same per-batch execution-view the
 * batch-execution page itself uses, keyed by batch_id, and offers step_id/recipe_step_code pairs. */
function BatchStepPickerField({
  value,
  onChange,
  entities,
}: {
  value: string;
  onChange: (value: string) => void;
  entities: ReturnType<typeof useEntityOptions>;
}) {
  const [batchId, setBatchId] = useState("");
  const { data: view, loading: stepsLoading, error: stepsError } = useApiResource<{
    steps: { step_id: string; recipe_step_code: string; state: string }[];
  }>(batchId ? `/batches/v1/${encodeURIComponent(batchId)}/execution-view` : null);
  const steps = view?.steps ?? [];

  return (
    <div className="grid grid-cols-2 gap-4">
      <EntityPickerField
        label="Batch"
        hint="The batch this sample was drawn from."
        value={batchId}
        onChange={(v) => {
          setBatchId(v);
          onChange("");
        }}
        options={entities.batches}
        status={entities.batchesStatus}
        kind="batch"
      />
      <Field label="Step" hint="The specific step this sample was drawn against.">
        <Select value={value} onChange={(e) => onChange(e.target.value)} disabled={!batchId || stepsLoading}>
          <option value="">{!batchId ? "—" : stepsLoading ? "Loading steps…" : steps.length ? "Select a step…" : "No steps found"}</option>
          {steps.map((s) => (
            <option key={s.step_id} value={s.step_id}>
              {s.recipe_step_code} ({s.state})
            </option>
          ))}
        </Select>
        {stepsError && <p className="error-text mt-2">Couldn&rsquo;t load steps for this batch.</p>}
      </Field>
    </div>
  );
}

function CreateSampleModal({ onClose, onDone }: { onClose: () => void; onDone: (id: string) => void }) {
  const [createdId, setCreatedId] = useState("");
  const { busy, error, run } = useCommand(() => onDone(createdId));
  const [sampleNumber, setSampleNumber] = useState("");
  const [sampleType, setSampleType] = useState(SAMPLE_TYPES[0]);
  const [sourceType, setSourceType] = useState(SOURCE_TYPES[0]);
  const [sourceId, setSourceId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [uom, setUom] = useState("g");
  const entities = useEntityOptions();

  return (
    <Modal open onClose={onClose} title="Create a QC sample" large>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(async () => {
            const receipt = await api.post<{ aggregate_id: string }>("/qc/v1/samples", {
              idempotency_key: newIdempotencyKey(),
              sample_number: sampleNumber,
              sample_type: sampleType,
              source_type: sourceType,
              source_id: sourceId || null,
              sample_quantity: quantity || null,
              sample_uom: uom || null,
            });
            setCreatedId(receipt.aggregate_id);
            return receipt;
          });
        }}
      >
        <div className="grid grid-cols-3 gap-4">
          <Field label="Sample number" required>
            <Input value={sampleNumber} onChange={(e) => setSampleNumber(e.target.value)} required autoFocus />
          </Field>
          <Field label="Sample type" required>
            <Select value={sampleType} onChange={(e) => setSampleType(e.target.value)}>
              {SAMPLE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Source type" required>
            <Select
              value={sourceType}
              // An id picked/typed for one source kind (a batch id, say) is meaningless once the kind
              // changes — clear it along with the switch rather than silently keep the stale value while
              // showing an unrelated picker (or the same generic text box, which is what made this look
              // like "nothing changed" before the picker branches below existed).
              onChange={(e) => {
                setSourceType(e.target.value);
                setSourceId("");
              }}
            >
              {SOURCE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        {sourceType === "batch" ? (
          <EntityPickerField
            label="Source record"
            hint="The batch this sample was drawn from."
            value={sourceId}
            onChange={setSourceId}
            options={entities.batches}
            status={entities.batchesStatus}
            kind="batch"
          />
        ) : sourceType === "batch_step" ? (
          <BatchStepPickerField value={sourceId} onChange={setSourceId} entities={entities} />
        ) : sourceType === "material_lot" ? (
          <EntityPickerField
            label="Source record"
            hint="The material lot this sample was drawn from."
            value={sourceId}
            onChange={setSourceId}
            options={entities.materialLots}
            status={entities.materialLotsStatus}
            kind="material lot"
          />
        ) : sourceType === "equipment" ? (
          <EntityPickerField
            label="Source record"
            hint="The equipment asset this sample was drawn from."
            value={sourceId}
            onChange={setSourceId}
            options={entities.equipment}
            status={entities.equipmentStatus}
            kind="equipment asset"
          />
        ) : (
          <Field
            label="Source reference"
            hint="No record list exists for this source type yet (environment/stability study) - enter a free-text reference."
          >
            <Input value={sourceId} onChange={(e) => setSourceId(e.target.value)} />
          </Field>
        )}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Sample quantity">
            <Input type="number" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          </Field>
          <UomSelect value={uom} onChange={setUom} />
        </div>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !sampleNumber.trim()}>
            {busy ? "Creating…" : "Create sample"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function NewSpecificationModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { busy, error, run } = useCommand(onDone);
  const [specCode, setSpecCode] = useState("");
  const [scopeType, setScopeType] = useState("product");
  const [scopeVersionId, setScopeVersionId] = useState("");
  const [definitions, setDefinitions] = useState<RepeatRow[]>([]);
  const { options: uomOptions, status: uomOptionsStatus } = useUomOptions();
  const { options: ruleOptions, status: ruleOptionsStatus } = useReleasedRuleOptions();
  const subFields = testDefinitionSubfields(uomOptions, uomOptionsStatus, ruleOptions, ruleOptionsStatus);

  return (
    <Modal open onClose={onClose} title="New test specification" large>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(() =>
            api.post("/qc/v1/specifications/drafts", {
              idempotency_key: newIdempotencyKey(),
              spec_code: specCode,
              scope_type: scopeType,
              scope_version_id: scopeVersionId,
              test_definitions: buildRepeatArray(subFields, definitions),
            })
          );
        }}
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="Spec code" required>
            <Input value={specCode} onChange={(e) => setSpecCode(e.target.value)} placeholder="e.g. QC-SPEC-PFS-001" required autoFocus />
          </Field>
          <Field label="Scope type" required>
            <Select
              value={scopeType}
              onChange={(e) => {
                setScopeType(e.target.value);
                setScopeVersionId("");
              }}
            >
              {SCOPE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        {scopeType === "product" ? (
          <ProductVersionPickerField
            label="Scope version ID"
            required
            hint="The product version this specification governs."
            value={scopeVersionId}
            onChange={setScopeVersionId}
          />
        ) : scopeType === "in_process" ? (
          <RecipeVersionPickerField
            label="Scope version ID"
            required
            hint="The recipe version this specification governs."
            value={scopeVersionId}
            onChange={setScopeVersionId}
          />
        ) : (
          <Field label="Scope version ID" required hint="The device version this specification governs.">
            <Input value={scopeVersionId} onChange={(e) => setScopeVersionId(e.target.value)} required />
          </Field>
        )}
        <RepeatableRows
          label="Test definitions"
          itemLabel="Test definition"
          hint="Every test this specification defines - at least one is required for a test order to ever be created against it."
          subFields={subFields}
          value={definitions}
          onChange={setDefinitions}
        />
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !specCode.trim() || !scopeVersionId.trim() || definitions.length === 0}>
            {busy ? "Creating…" : "Create draft"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function NewQcMethodDraftModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { busy, error, run } = useCommand(onDone);
  const { siteId } = useSiteId();
  const [methodCode, setMethodCode] = useState("");
  const [methodType, setMethodType] = useState("internal");
  const [name, setName] = useState("");
  const [validationEvidenceReference, setValidationEvidenceReference] = useState("");
  const [modificationReason, setModificationReason] = useState("");

  return (
    <Modal open onClose={onClose} title="New QC method draft">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!siteId) return;
          run(() =>
            api.post("/qc/v1/methods/drafts", {
              idempotency_key: newIdempotencyKey(),
              method_code: methodCode,
              method_type: methodType,
              name,
              site_id: siteId,
              validation_evidence_reference: validationEvidenceReference || null,
              modification_reason: modificationReason || null,
            })
          );
        }}
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="Method code" required>
            <Input value={methodCode} onChange={(e) => setMethodCode(e.target.value)} placeholder="e.g. HPLC-ASSAY-001" required autoFocus />
          </Field>
          <Field label="Method type" required>
            <Select value={methodType} onChange={(e) => setMethodType(e.target.value)}>
              {QC_METHOD_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Name" required>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
        </div>
        <Field label="Validation evidence reference" hint="Required in practice for a validated method - not enforced client-side.">
          <Input value={validationEvidenceReference} onChange={(e) => setValidationEvidenceReference(e.target.value)} />
        </Field>
        <Field label="Modification reason" hint="Set when this draft supersedes a prior released version.">
          <textarea className="input" rows={2} value={modificationReason} onChange={(e) => setModificationReason(e.target.value)} />
        </Field>
        {error && <p className="error-text mb-2">{error}</p>}
        <div className="flex justify-between gap-3 mt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy || !methodCode.trim() || !name.trim() || !siteId}>
            {busy ? "Creating…" : "Create draft"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
