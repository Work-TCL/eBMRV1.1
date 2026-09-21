"use client";

import { useState } from "react";
import { api, ApiError, newIdempotencyKey, type MutationReceipt } from "@/lib/api";
import { useEntityOptions, type EntityOption, type EntityOptionsStatus } from "@/lib/hooks";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import {
  RepeatableRows,
  KeyValueRows,
  StringListRows,
  buildKvObject,
  buildRepeatArray,
  buildStringList,
  type RepeatRow,
  type KvRow,
  type RepeatSubField,
} from "@/components/shared/RepeatableFields";

export interface FormField {
  name: string;
  label: string;
  type?:
    | "text"
    | "number"
    | "date"
    | "datetime"
    | "select"
    | "textarea"
    | "json"
    | "bool"
    // Added for structured-data forms (DDCP-style): a batch/equipment picker instead of a raw id, a
    // repeatable row group instead of a JSON array, and a free-form key/value editor instead of a raw
    // JSON object. None of the existing types above changed behaviour — these are purely additive.
    | "batchSelect"
    | "equipmentSelect"
    | "areaSelect"
    | "userSelect"
    // `owner_type`/`owner_id` pair for a polymorphic-owner command (e.g. evidence staging). `owner_type`
    // has no backend enum (it's a free String(80) column — grep-verified across every module), so
    // "ownerTypeSelect" offers only the values this codebase actually creates evidence against today
    // ("batch_step", "gxp_batch") plus an "Other…" escape hatch to free text — never a closed dropdown
    // that could block a real owner_type this list doesn't happen to know about. "ownerIdSelect" reads
    // the sibling "owner_type" field's current value and swaps in the matching picker: batch→step
    // cascade, a plain batch picker, or free text for "Other".
    | "ownerTypeSelect"
    | "ownerIdSelect"
    // A file picker for a command field the backend expects as base64 content (e.g. evidence upload) —
    // reads the chosen file client-side and stores its base64 encoding, so the operator picks a file
    // instead of pasting a base64 blob into a text box.
    | "fileBase64"
    // An evidence object picker: the caller enters the owner_type/owner_id the evidence was staged
    // under (self-contained, not sent as form fields — GET /evidence/v1/objects has no unfiltered list,
    // Document 72 declares none, so it must stay owner-scoped) and picks from the resulting list instead
    // of pasting a raw evidence_id UUID. Manual-ID fallback available, same as every other picker type.
    | "evidenceSelect"
    | "repeat"
    | "kv"
    | "stringList";
  required?: boolean;
  hint?: string;
  placeholder?: string;
  options?: { value: string; label: string }[];
  /** Seed value. */
  default?: string;
  /** "repeat" only — the shape of each row. */
  subFields?: RepeatSubField[];
  /** "repeat" only — used in "Add …" / "Remove …" text. Defaults to `label`. */
  itemLabel?: string;
  /** Set only for a field whose name fills a `{placeholder}` in the path but is NOT itself a field on
   * the command model (rare — most path ids are also required in the body, and are sent there by
   * default). Every command in this API sets `extra="forbid"`, so a path-only field must be excluded
   * from the body rather than merely duplicated. */
  pathOnly?: boolean;
}

export interface FormOp {
  /** Path after `root`, e.g. `safety-cases/{case_id}/classifications`. Any `{name}` placeholder is
   * substituted from the field of that name before the request (and that field is not also sent in
   * the body). */
  path: string;
  label: string;
  method?: "GET" | "POST";
  /** Structured fields. When omitted, a single JSON body textarea is shown instead. */
  fields?: FormField[];
  /** Seed JSON for the fallback textarea (only used when `fields` is omitted). */
  template?: string;
  /** One-line description shown under the operation selector. */
  about?: string;
}

export function coerce(field: FormField, raw: string): unknown {
  const v = raw.trim();
  if (v === "") return field.required ? "" : null;
  switch (field.type) {
    case "number":
      return Number(v);
    case "bool":
      return v === "true" || v === "yes" || v === "1";
    case "json":
      return JSON.parse(v);
    case "date":
    case "datetime":
      return new Date(v).toISOString();
    default:
      return v;
  }
}

export type ComplexValues = Record<string, RepeatRow[] | KvRow[] | string[]>;

export function seedFieldValues(fields: FormField[]): Record<string, string> {
  const s: Record<string, string> = {};
  for (const f of fields) if (f.default !== undefined) s[f.name] = f.default;
  return s;
}

export function seedComplexValues(fields: FormField[]): ComplexValues {
  const s: ComplexValues = {};
  for (const f of fields) if (f.type === "repeat" || f.type === "kv" || f.type === "stringList") s[f.name] = [];
  return s;
}

/** Assembles the exact request body a set of `FormField`s describes — shared by `FormConsole` and
 * `SignedJsonForm` so a signed operation with a flat-ish payload gets the same structured controls
 * (and the same field-to-JSON assembly) as an unsigned one, instead of a bespoke copy. */
export function buildFieldsBody(fields: FormField[], values: Record<string, string>, complexValues: ComplexValues): Record<string, unknown> {
  const body: Record<string, unknown> = {};
  for (const f of fields) {
    // A field named after a `{placeholder}` in the path is NOT skipped here by default — every
    // mutation endpoint in this API that takes an id in its URL also requires that same id in
    // the body and checks the two match ("X in path and body must match", grep-verified across
    // every module), and every command model sets extra="forbid", so omitting it doesn't fall
    // back to "the router already has it from the path" — it fails with a missing-field 422
    // instead. The rare field that fills a path placeholder without being a real body field
    // opts out explicitly via `pathOnly` (extra="forbid" would reject it as an unknown field).
    if (f.pathOnly) continue;
    if (f.type === "repeat") {
      body[f.name] = buildRepeatArray(f.subFields ?? [], (complexValues[f.name] as RepeatRow[]) ?? []);
      continue;
    }
    if (f.type === "kv") {
      body[f.name] = buildKvObject((complexValues[f.name] as KvRow[]) ?? []);
      continue;
    }
    if (f.type === "stringList") {
      body[f.name] = buildStringList((complexValues[f.name] as string[]) ?? []);
      continue;
    }
    const c = coerce(f, values[f.name] ?? "");
    if (c !== null) body[f.name] = c;
  }
  return body;
}

export function missingRequiredFields(fields: FormField[], values: Record<string, string>, complexValues: ComplexValues): boolean {
  return fields.some((f) => {
    if (!f.required) return false;
    if (f.type === "repeat") return ((complexValues[f.name] as RepeatRow[]) ?? []).length === 0;
    // A free-form settings field usually has no meaningful "empty" state — but a handful of backend
    // commands do require at least one key (e.g. a classification payload), so `required` still gates.
    if (f.type === "kv") return !((complexValues[f.name] as KvRow[]) ?? []).some((r) => r.key.trim());
    if (f.type === "stringList") return buildStringList((complexValues[f.name] as string[]) ?? []).length === 0;
    return !(values[f.name] ?? "").trim();
  });
}

/** Renders one `FormField[]` as the app's standard two-column grid — foreign-key pickers, repeat/kv/
 * string-list editors, and plain inputs alike. Shared by `FormConsole` and `SignedJsonForm` so the two
 * consoles never grow two different renderings of the same field vocabulary. */
export function FormFieldsGrid({
  fields,
  values,
  setValues,
  complexValues,
  setComplexValues,
  entities,
}: {
  fields: FormField[];
  values: Record<string, string>;
  setValues: (updater: (c: Record<string, string>) => Record<string, string>) => void;
  complexValues: ComplexValues;
  setComplexValues: (updater: (c: ComplexValues) => ComplexValues) => void;
  entities: ReturnType<typeof useEntityOptions>;
}) {
  return (
    <div className="grid grid-cols-2 gap-4">
      {fields.map((f) =>
        f.type === "repeat" ? (
          <div key={f.name} style={{ gridColumn: "1 / -1" }}>
            <RepeatableRows
              label={f.label}
              required={f.required}
              hint={f.hint}
              itemLabel={f.itemLabel}
              subFields={f.subFields ?? []}
              value={(complexValues[f.name] as RepeatRow[]) ?? []}
              onChange={(rows) => setComplexValues((c) => ({ ...c, [f.name]: rows }))}
              materialLotOptions={entities.materialLots}
              materialLotOptionsStatus={entities.materialLotsStatus}
              userOptions={entities.users}
              userOptionsStatus={entities.usersStatus}
              equipmentOptions={entities.equipment}
              equipmentOptionsStatus={entities.equipmentStatus}
              areaOptions={entities.areas}
              areaOptionsStatus={entities.areasStatus}
            />
          </div>
        ) : f.type === "kv" ? (
          <div key={f.name} style={{ gridColumn: "1 / -1" }}>
            <KeyValueRows
              label={f.label}
              hint={f.hint}
              value={(complexValues[f.name] as KvRow[]) ?? []}
              onChange={(rows) => setComplexValues((c) => ({ ...c, [f.name]: rows }))}
            />
          </div>
        ) : f.type === "stringList" ? (
          <div key={f.name} style={{ gridColumn: "1 / -1" }}>
            <StringListRows
              label={f.label}
              required={f.required}
              hint={f.hint}
              itemLabel={f.itemLabel}
              placeholder={f.placeholder}
              value={(complexValues[f.name] as string[]) ?? []}
              onChange={(rows) => setComplexValues((c) => ({ ...c, [f.name]: rows }))}
            />
          </div>
        ) : f.type === "batchSelect" ? (
          <EntityPickerField
            key={f.name}
            label={f.label}
            required={f.required}
            hint={f.hint}
            value={values[f.name] ?? ""}
            onChange={(v) => setValues((c) => ({ ...c, [f.name]: v }))}
            options={entities.batches}
            status={entities.batchesStatus}
            kind="batch"
          />
        ) : f.type === "equipmentSelect" ? (
          <EntityPickerField
            key={f.name}
            label={f.label}
            required={f.required}
            hint={f.hint}
            value={values[f.name] ?? ""}
            onChange={(v) => setValues((c) => ({ ...c, [f.name]: v }))}
            options={entities.equipment}
            status={entities.equipmentStatus}
            kind="equipment asset"
          />
        ) : f.type === "areaSelect" ? (
          <EntityPickerField
            key={f.name}
            label={f.label}
            required={f.required}
            hint={f.hint}
            value={values[f.name] ?? ""}
            onChange={(v) => setValues((c) => ({ ...c, [f.name]: v }))}
            options={entities.areas}
            status={entities.areasStatus}
            kind="equipment area"
          />
        ) : f.type === "userSelect" ? (
          <EntityPickerField
            key={f.name}
            label={f.label}
            required={f.required}
            hint={f.hint}
            value={values[f.name] ?? ""}
            onChange={(v) => setValues((c) => ({ ...c, [f.name]: v }))}
            options={entities.users}
            status={entities.usersStatus}
            kind="user"
          />
        ) : f.type === "ownerTypeSelect" ? (
          <OwnerTypeField
            key={f.name}
            label={f.label}
            required={f.required}
            hint={f.hint}
            value={values[f.name] ?? ""}
            onChange={(v) => setValues((c) => ({ ...c, [f.name]: v }))}
          />
        ) : f.type === "ownerIdSelect" ? (
          values.owner_type === "batch_step" ? (
            <BatchStepOwnerPicker
              key={f.name}
              label={f.label}
              required={f.required}
              hint={f.hint}
              value={values[f.name] ?? ""}
              onChange={(stepId) => setValues((c) => ({ ...c, [f.name]: stepId }))}
              batchOptions={entities.batches}
              batchOptionsStatus={entities.batchesStatus}
            />
          ) : values.owner_type === "gxp_batch" ? (
            <EntityPickerField
              key={f.name}
              label={f.label}
              required={f.required}
              hint={f.hint}
              value={values[f.name] ?? ""}
              onChange={(v) => setValues((c) => ({ ...c, [f.name]: v }))}
              options={entities.batches}
              status={entities.batchesStatus}
              kind="batch"
            />
          ) : (
            <Field key={f.name} label={f.label} required={f.required} hint={f.hint ?? "Select an owner type above first."}>
              <Input
                type="text"
                value={values[f.name] ?? ""}
                onChange={(e) => setValues((c) => ({ ...c, [f.name]: e.target.value }))}
                placeholder="Owner ID"
              />
            </Field>
          )
        ) : f.type === "evidenceSelect" ? (
          <EvidenceObjectOwnerPicker
            key={f.name}
            label={f.label}
            required={f.required}
            hint={f.hint}
            value={values[f.name] ?? ""}
            onChange={(v) => setValues((c) => ({ ...c, [f.name]: v }))}
            batchOptions={entities.batches}
            batchOptionsStatus={entities.batchesStatus}
          />
        ) : f.type === "fileBase64" ? (
          <FileBase64Field
            key={f.name}
            label={f.label}
            required={f.required}
            hint={f.hint}
            onChange={(v) => setValues((c) => ({ ...c, [f.name]: v }))}
          />
        ) : (
          <Field key={f.name} label={f.label} required={f.required} hint={f.hint}>
            {f.type === "select" ? (
              <Select value={values[f.name] ?? ""} onChange={(e) => setValues((c) => ({ ...c, [f.name]: e.target.value }))}>
 <option value=""></option>
                {(f.options ?? []).map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </Select>
            ) : f.type === "bool" ? (
              <Select value={values[f.name] ?? ""} onChange={(e) => setValues((c) => ({ ...c, [f.name]: e.target.value }))}>
 <option value=""></option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </Select>
            ) : f.type === "textarea" || f.type === "json" ? (
              <textarea
                className="input"
                rows={f.type === "json" ? 4 : 2}
                value={values[f.name] ?? ""}
                onChange={(e) => setValues((c) => ({ ...c, [f.name]: e.target.value }))}
                placeholder={f.placeholder ?? (f.type === "json" ? "{ }" : undefined)}
                spellCheck={false}
              />
            ) : (
              <Input
                type={f.type === "number" ? "number" : f.type === "date" ? "date" : f.type === "datetime" ? "datetime-local" : "text"}
                value={values[f.name] ?? ""}
                onChange={(e) => setValues((c) => ({ ...c, [f.name]: e.target.value }))}
                placeholder={f.placeholder}
              />
            )}
          </Field>
        )
      )}
    </div>
  );
}

/** Reads a chosen file client-side and reports its base64 content — for the rare command field the
 * backend expects as a base64 string (e.g. evidence upload content) — so the operator picks a file
 * instead of pasting a base64 blob into a text box. Nothing is uploaded here; the parent form still
 * submits the base64 string as an ordinary field value through the normal Mutation Gateway call. */
function FileBase64Field({
  label,
  required,
  hint,
  onChange,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  onChange: (base64: string) => void;
}) {
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function handleFile(file: File | undefined) {
    if (!file) {
      setFileName(null);
      onChange("");
      return;
    }
    setError(null);
    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      // A `readAsDataURL` result is "data:<mime>;base64,<content>" — the command field wants just
      // <content>.
      const base64 = result.includes(",") ? result.slice(result.indexOf(",") + 1) : result;
      setFileName(file.name);
      onChange(base64);
    };
    reader.onerror = () => setError("Could not read that file.");
    reader.readAsDataURL(file);
  }

  return (
    <Field label={label} required={required} hint={hint} error={error}>
      <input
        type="file"
        className="input"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      {fileName && <p className="hint mt-1">Selected: {fileName}</p>}
    </Field>
  );
}

const pickerLinkStyle = {
  background: "none",
  border: "none",
  padding: 0,
  color: "var(--brand-600)",
  fontSize: "var(--fs-2)",
  cursor: "pointer",
  textDecoration: "underline",
} as const;

/** The only `owner_type` values this codebase actually stages evidence against today (grep-verified:
 * `batch_step` in the batch-execution "Link evidence" flow, `gxp_batch` in the evidence lifecycle test
 * suite). `owner_type` itself has no backend enum — it's a free `String(80)` column — so this is a
 * convenience shortlist, never a hard restriction: "Other…" drops to free text for anything else. */
const KNOWN_OWNER_TYPES = [
  { value: "batch_step", label: "Batch step" },
  { value: "gxp_batch", label: "Batch (whole)" },
];

function OwnerTypeField({
  label,
  required,
  hint,
  value,
  onChange,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const isKnown = KNOWN_OWNER_TYPES.some((o) => o.value === value);
  const [manual, setManual] = useState(value !== "" && !isKnown);

  if (manual) {
    return (
      <Field label={label} required={required} hint={hint}>
        <Input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder="Owner type" />
        <button
          type="button"
          style={{ ...pickerLinkStyle, marginTop: 6 }}
          onClick={() => {
            setManual(false);
            onChange("");
          }}
        >
          Choose from list instead
        </button>
      </Field>
    );
  }

  return (
    <Field label={label} required={required} hint={hint}>
      <Select
        value={value}
        onChange={(e) => {
          if (e.target.value === "__other__") {
            setManual(true);
            onChange("");
          } else {
            onChange(e.target.value);
          }
        }}
      >
        <option value="">Select an owner type</option>
        {KNOWN_OWNER_TYPES.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
        <option value="__other__">Other…</option>
      </Select>
    </Field>
  );
}

/** Batch → step cascading picker, for a field referencing one specific batch step (e.g. evidence
 * staging's "Owner ID" when "Owner type" is "batch_step") — the batch id alone isn't the field's value,
 * so a plain `EntityPickerField` (one flat list) doesn't fit; this fetches the chosen batch's steps on
 * demand rather than every step of every batch up front. Falls back to a manual-ID `Input` the same way
 * every other "*Select" type does, for any owner_type this picker doesn't cover. */
function BatchStepOwnerPicker({
  label,
  required,
  hint,
  value,
  onChange,
  batchOptions,
  batchOptionsStatus,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  value: string;
  onChange: (stepId: string) => void;
  batchOptions: EntityOption[];
  batchOptionsStatus: EntityOptionsStatus;
}) {
  const [manual, setManual] = useState(false);
  const [batchId, setBatchId] = useState("");
  const [steps, setSteps] = useState<{ step_id: string; recipe_step_code: string }[]>([]);
  const [stepsStatus, setStepsStatus] = useState<EntityOptionsStatus>("empty");

  function selectBatch(id: string) {
    setBatchId(id);
    setSteps([]);
    if (!id) {
      setStepsStatus("empty");
      return;
    }
    setStepsStatus("loading");
    api
      .get<{ steps: { step_id: string; recipe_step_code: string }[] }>(`/batches/v1/${id}/execution-view`)
      .then((res) => {
        setSteps(res.steps);
        setStepsStatus(res.steps.length ? "ready" : "empty");
      })
      .catch(() => setStepsStatus("error"));
  }

  if (manual || batchOptionsStatus === "error") {
    return (
      <Field label={label} required={required} hint={hint}>
        <Input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder="Owner ID" />
        {batchOptionsStatus !== "error" && (
          <button type="button" style={{ ...pickerLinkStyle, marginTop: 6 }} onClick={() => setManual(false)}>
            Pick a batch step instead
          </button>
        )}
      </Field>
    );
  }

  return (
    <Field label={label} required={required} hint={hint}>
      <Select value={batchId} onChange={(e) => selectBatch(e.target.value)} disabled={batchOptionsStatus === "loading"}>
        <option value="">{batchOptionsStatus === "loading" ? "Loading batches…" : "Select a batch"}</option>
        {batchOptions.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </Select>
      {batchId && (
        <Select value={value} onChange={(e) => onChange(e.target.value)} disabled={stepsStatus === "loading"} style={{ marginTop: 6 }}>
          <option value="">{stepsStatus === "loading" ? "Loading steps…" : "Select a step"}</option>
          {steps.map((s) => (
            <option key={s.step_id} value={s.step_id}>
              {s.recipe_step_code}
            </option>
          ))}
        </Select>
      )}
      <button type="button" style={{ ...pickerLinkStyle, marginTop: 6 }} onClick={() => setManual(true)}>
        Not a batch step? Enter the owner ID manually
      </button>
    </Field>
  );
}

interface EvidenceObjectRow {
  id: string;
  filename: string | null;
  state: string;
  content_hash: string | null;
}

/** Picks an evidence object by its real id instead of a pasted (and easily mistyped/truncated) UUID —
 * the bug this fixes: "Finalize an upload", "Apply a legal hold" and "Download evidence" all took a
 * free-text `evidence_id` with nothing to copy it from. `GET /evidence/v1/objects` has no unfiltered
 * list (Document 72 declares none), so the operator scopes by owner first — the same `KNOWN_OWNER_TYPES`
 * shortlist and batch/step cascade as `OwnerTypeField`/`BatchStepOwnerPicker` above, so picking an owner
 * here feels identical to picking one when staging — then picks from that owner's evidence objects.
 * The owner scope is local state only, never part of the submitted form fields (only the chosen
 * evidence_id is). */
export function EvidenceObjectOwnerPicker({
  label,
  required,
  hint,
  value,
  onChange,
  batchOptions,
  batchOptionsStatus,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  value: string;
  onChange: (evidenceId: string) => void;
  batchOptions: EntityOption[];
  batchOptionsStatus: EntityOptionsStatus;
}) {
  const [manualEvidence, setManualEvidence] = useState(false);
  const [ownerKind, setOwnerKind] = useState<"batch_step" | "gxp_batch" | "other">("batch_step");
  const [batchId, setBatchId] = useState("");
  const [stepId, setStepId] = useState("");
  const [steps, setSteps] = useState<{ step_id: string; recipe_step_code: string }[]>([]);
  const [stepsStatus, setStepsStatus] = useState<EntityOptionsStatus>("empty");
  const [manualOwnerType, setManualOwnerType] = useState("");
  const [manualOwnerId, setManualOwnerId] = useState("");
  const [rows, setRows] = useState<EvidenceObjectRow[]>([]);
  const [status, setStatus] = useState<EntityOptionsStatus>("empty");

  function fetchObjects(ot: string, oid: string) {
    if (!ot.trim() || !oid.trim()) {
      setRows([]);
      setStatus("empty");
      return;
    }
    setStatus("loading");
    api
      .get<{ evidence_objects: EvidenceObjectRow[] }>(
        `/evidence/v1/objects?owner_type=${encodeURIComponent(ot.trim())}&owner_id=${encodeURIComponent(oid.trim())}`
      )
      .then((res) => {
        setRows(res.evidence_objects);
        setStatus(res.evidence_objects.length ? "ready" : "empty");
      })
      .catch(() => setStatus("error"));
  }

  function resetScope(kind: "batch_step" | "gxp_batch" | "other") {
    setOwnerKind(kind);
    setBatchId("");
    setStepId("");
    setSteps([]);
    setStepsStatus("empty");
    setManualOwnerType("");
    setManualOwnerId("");
    setRows([]);
    setStatus("empty");
    onChange("");
  }

  function selectBatchForStep(id: string) {
    setBatchId(id);
    setStepId("");
    setSteps([]);
    onChange("");
    setRows([]);
    setStatus("empty");
    if (!id) {
      setStepsStatus("empty");
      return;
    }
    setStepsStatus("loading");
    api
      .get<{ steps: { step_id: string; recipe_step_code: string }[] }>(`/batches/v1/${id}/execution-view`)
      .then((res) => {
        setSteps(res.steps);
        setStepsStatus(res.steps.length ? "ready" : "empty");
      })
      .catch(() => setStepsStatus("error"));
  }

  function selectStep(id: string) {
    setStepId(id);
    fetchObjects("batch_step", id);
  }

  function selectBatchForWhole(id: string) {
    setBatchId(id);
    fetchObjects("gxp_batch", id);
  }

  if (manualEvidence) {
    return (
      <Field label={label} required={required} hint={hint}>
        <Input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder="Evidence object ID" />
        <button type="button" style={{ ...pickerLinkStyle, marginTop: 6 }} onClick={() => setManualEvidence(false)}>
          Pick from a list instead
        </button>
      </Field>
    );
  }

  return (
    <Field label={label} required={required} hint={hint ?? "Pick the owner this evidence was staged under, then select it below."}>
      <Select value={ownerKind} onChange={(e) => resetScope(e.target.value as "batch_step" | "gxp_batch" | "other")}>
        <option value="batch_step">Owner: Batch step</option>
        <option value="gxp_batch">Owner: Batch (whole)</option>
        <option value="other">Owner: Other…</option>
      </Select>

      {ownerKind === "batch_step" && (
        <>
          <Select
            value={batchId}
            onChange={(e) => selectBatchForStep(e.target.value)}
            disabled={batchOptionsStatus === "loading"}
            style={{ marginTop: 6 }}
          >
            <option value="">{batchOptionsStatus === "loading" ? "Loading batches…" : "Select a batch"}</option>
            {batchOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
          {batchId && (
            <Select value={stepId} onChange={(e) => selectStep(e.target.value)} disabled={stepsStatus === "loading"} style={{ marginTop: 6 }}>
              <option value="">{stepsStatus === "loading" ? "Loading steps…" : "Select a step"}</option>
              {steps.map((s) => (
                <option key={s.step_id} value={s.step_id}>
                  {s.recipe_step_code}
                </option>
              ))}
            </Select>
          )}
        </>
      )}

      {ownerKind === "gxp_batch" && (
        <Select
          value={batchId}
          onChange={(e) => selectBatchForWhole(e.target.value)}
          disabled={batchOptionsStatus === "loading"}
          style={{ marginTop: 6 }}
        >
          <option value="">{batchOptionsStatus === "loading" ? "Loading batches…" : "Select a batch"}</option>
          {batchOptions.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
      )}

      {ownerKind === "other" && (
        <div className="grid grid-cols-2 gap-2" style={{ marginTop: 6 }}>
          <Input
            type="text"
            value={manualOwnerType}
            onChange={(e) => setManualOwnerType(e.target.value)}
            onBlur={() => fetchObjects(manualOwnerType, manualOwnerId)}
            placeholder="Owner type"
          />
          <Input
            type="text"
            value={manualOwnerId}
            onChange={(e) => setManualOwnerId(e.target.value)}
            onBlur={() => fetchObjects(manualOwnerType, manualOwnerId)}
            placeholder="Owner ID"
          />
        </div>
      )}

      <Select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={status !== "ready"}
        style={{ marginTop: 6 }}
      >
        <option value="">
          {status === "loading"
            ? "Loading evidence objects…"
            : status === "error"
              ? "Couldn't load — enter the ID manually below"
              : status === "empty"
                ? "No evidence objects found for this owner"
                : "Select an evidence object"}
        </option>
        {rows.map((r) => (
          <option key={r.id} value={r.id}>
            {`${r.filename ?? r.id} — ${r.state}${r.content_hash ? ` (${r.content_hash.slice(0, 10)}…)` : ""}`}
          </option>
        ))}
      </Select>
      <button type="button" style={{ ...pickerLinkStyle, marginTop: 6 }} onClick={() => setManualEvidence(true)}>
        Enter the evidence object ID manually
      </button>
    </Field>
  );
}

/**
 * A friendlier operations console: pick an operation, fill labelled fields (or a JSON body for the
 * genuinely nested ones), submit. Structured fields are coerced (number / bool / date → ISO / JSON)
 * and `idempotency_key` is added to every POST. Supersedes the raw-JSON `JsonOpConsole` for surfaces
 * whose payloads are mostly flat.
 */
export function FormConsole({
  title,
  subtitle,
  root,
  ops,
}: {
  title: string;
  subtitle?: string;
  root: string;
  ops: FormOp[];
}) {
  const [idx, setIdx] = useState(0);
  const op = ops[idx];
  const [values, setValues] = useState<Record<string, string>>(() => seedFieldValues(ops[0]?.fields ?? []));
  const [complexValues, setComplexValues] = useState<ComplexValues>(() => seedComplexValues(ops[0]?.fields ?? []));
  const [jsonBody, setJsonBody] = useState(ops[0]?.template ?? "{\n  \n}");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(undefined);
  const entities = useEntityOptions();

  function selectOp(next: number) {
    setIdx(next);
    setValues(seedFieldValues(ops[next]?.fields ?? []));
    setComplexValues(seedComplexValues(ops[next]?.fields ?? []));
    setJsonBody(ops[next]?.template ?? "{\n  \n}");
    setError(null);
    setResult(undefined);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setResult(undefined);
    try {
      const filledPath = op.path.replace(/\{(\w+)\}/g, (_, name) => encodeURIComponent((values[name] ?? "").trim()));
      const url = `${root}/${filledPath}`;
      if (op.method === "GET") {
        setResult(await api.get<unknown>(url));
      } else {
        const body = op.fields ? buildFieldsBody(op.fields, values, complexValues) : jsonBody.trim() ? JSON.parse(jsonBody) : {};
        setResult(await api.post<MutationReceipt>(url, { idempotency_key: newIdempotencyKey(), ...body }));
      }
    } catch (err) {
      if (err instanceof SyntaxError) setError(`Invalid JSON: ${err.message}`);
      else setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  const missingRequired = op.fields ? missingRequiredFields(op.fields, values, complexValues) : false;

  return (
    <Card pad className="mb-4">
      <CardHeader title={title} />
      {subtitle && <p className="fs-2 text-muted mb-3">{subtitle}</p>}
      <form onSubmit={submit}>
        <Field label="Operation">
          <Select value={idx} onChange={(e) => selectOp(Number(e.target.value))}>
            {ops.map((o, i) => (
              <option key={o.path + o.label} value={i}>
                {o.label}
              </option>
            ))}
          </Select>
        </Field>
        {op.about && <p className="fs-2 text-muted mb-3">{op.about}</p>}

        {op.fields ? (
          <FormFieldsGrid
            fields={op.fields}
            values={values}
            setValues={setValues}
            complexValues={complexValues}
            setComplexValues={setComplexValues}
            entities={entities}
          />
        ) : op.method === "GET" ? null : (
          <Field label="Payload (JSON)" hint="This operation has a nested payload - see the API contract.">
            <textarea
              className="input"
              rows={10}
              value={jsonBody}
              onChange={(e) => setJsonBody(e.target.value)}
              spellCheck={false}
            />
          </Field>
        )}

        {error && <p className="error-text mt-2">{error}</p>}
        <Button type="submit" variant="primary" disabled={busy || missingRequired} className="mt-3">
          {busy ? "Working…" : op.method === "GET" ? "Fetch" : "Submit"}
        </Button>
      </form>
      {result !== undefined && (
        <div className="mt-3">
          <JsonPanel title="Response" value={result} />
        </div>
      )}
    </Card>
  );
}
