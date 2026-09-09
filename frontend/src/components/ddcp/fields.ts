/**
 * Data-transformation layer for the DDCP execution/profile forms (spec section 18): a `DdcpField[]`
 * describes one backend command's shape in human terms, `DdcpFormState` is the controlled form state,
 * and `buildPayload()` turns that state into exactly the JSON body the existing DDCP API already
 * expects — no backend contract changes. Field names always match the backend command's own field
 * names 1:1 (see `catalog.ts`), so this stays a pure presentation/assembly layer, never a guess at
 * business rules.
 */

export type DdcpFieldType =
  | "text"
  | "number" // integer
  | "decimal" // decimal-as-string — never coerced to a JS number (AG-15 / DATA-FR-019)
  | "datetime"
  | "bool"
  | "select"
  | "batchSelect"
  | "equipmentSelect"
  | "areaSelect"
  | "profileSelect" // a family-scoped DDCP profile picker (see catalog.ts's DdcpFamily.prefix)
  | "productVersionSelect" // SG-175: a two-step Product Master picker (business ID, then that
  // product's RELEASED versions) — used only by product_version_id on the profile-create form,
  // there is no flat "all product versions" list endpoint to pick from directly
  | "recordSelect" // an id picked from records created earlier this session (see catalog.ts's DdcpOp.producesRecordKind) — falls back to manual entry, same as the other pickers
  | "sterilizationSelect" // GET /sterilization/v1/items/eligible (SG-179 follow-up) — a completed
  // sterilization load item or filter use, site-scoped; used only by sterilization_use_id
  | "ruleSelect" // GET /rules/v1 — a rule with a currently-effective RELEASED version, by its rule_id
  // (a human string, not a uuid); same list recipe_master's condition_rule_id picker already uses.
  // Used by every acceptance_rule_id (fill IPC's "no effective released version" 404 otherwise).
  | "asepticInterventionSelect" // GET /aseptic/v1/interventions — a real AsepticIntervention id,
  // site-scoped; used only by source_aseptic_intervention_id on "Record an aseptic intervention"
  | "ref" // a small {chosen-key: value} reference object, e.g. source_batch_reference
  | "repeat" // an array of objects built from subFields, e.g. constituent_requirements
  | "kv" // a free-form {key: value} object, e.g. constituent_architecture — the backend stores this
  // verbatim with no fixed schema; nothing here is validated, so there is no hidden key catalogue to
  // discover (see each field's own hint for the one or two keys the backend actually reads, if any)
  | "boolKv"; // a single-key {kvKey: true|false} object — for the rare kv field where the backend
  // actually reads one specific boolean key (e.g. environment_status.ready) rather than treating the
  // whole object as opaque; renders as a plain Yes/No control instead of asking the user to know and
  // type that key by hand.

export interface SelectOption {
  value: string;
  label: string;
}

export interface DdcpField {
  name: string;
  label: string;
  type: DdcpFieldType;
  required?: boolean;
  hint?: string;
  placeholder?: string;
  /** "select" only. */
  options?: SelectOption[];
  /** "text" only — documented common values offered as suggestions (native `<datalist>`) without
   * restricting entry to them. Used for the handful of DDCP vocabularies (test_type, count_type, …)
   * the backend documents but does not enforce as a closed set at the command layer — a hard `select`
   * there would silently remove capability the API still accepts. */
  suggestions?: SelectOption[];
  /** "ref" only — the allowed key names for the reference object (e.g. batch_id vs lot_id). */
  refKeys?: SelectOption[];
  refValuePlaceholder?: string;
  /** "repeat" only — the shape of each row. */
  subFields?: DdcpField[];
  /** "repeat" only — used in "+ Add sample" / "Remove sample" button text. Defaults to the label. */
  itemLabel?: string;
  /** "boolKv" only — the single object key this field's Yes/No answer is written under, e.g. "ready". */
  kvKey?: string;
  /** "recordSelect" only — matches some earlier op's `producesRecordKind` in the same family (see
   * catalog.ts) — this field offers, as a dropdown, every id of that kind created so far this session
   * (e.g. a handoff id offered to "Accept or reject a constituent handoff"'s Handoff ID field right
   * after "Record a constituent handoff" created one), alongside the usual manual-entry fallback. */
  recordKind?: string;
  /** "recordSelect" only — the human word for one row of that kind, used in "No {kind}s available yet."
   * and "Choose a {kind}" copy (e.g. "handoff", "fill operation", "assembly record"). */
  pickerKind?: string;
  default?: string;
}

export interface RefValue {
  key: string;
  value: string;
}
export type RepeatRow = Record<string, string>;
export interface KvRow {
  key: string;
  value: string;
}
export type FieldValue = string | RefValue | RepeatRow[] | KvRow[];
export type DdcpFormState = Record<string, FieldValue>;

export function initFieldValue(field: DdcpField): FieldValue {
  switch (field.type) {
    case "ref":
      return { key: field.refKeys?.[0]?.value ?? "", value: "" };
    case "repeat":
    case "kv":
      return [];
    default:
      return field.default ?? "";
  }
}

export function initState(fields: DdcpField[], seeds?: Record<string, string>): DdcpFormState {
  const state: DdcpFormState = {};
  for (const f of fields) {
    state[f.name] = seeds?.[f.name] !== undefined && f.type !== "ref" && f.type !== "repeat" && f.type !== "kv"
      ? (seeds[f.name] as FieldValue)
      : initFieldValue(f);
  }
  return state;
}

/** Names referenced as `{name}` in an operation path — filled from the URL, never sent in the body
 * (matches the convention `FormConsole` already established for other write-heavy pages). */
export function pathParamNames(path: string): Set<string> {
  return new Set(Array.from(path.matchAll(/\{(\w+)\}/g), (m) => m[1]));
}

export function isFieldFilled(field: DdcpField, value: FieldValue): boolean {
  switch (field.type) {
    case "ref": {
      const v = value as RefValue;
      return !!v?.key && !!v.value?.trim();
    }
    case "repeat":
      return Array.isArray(value) && (value as RepeatRow[]).length > 0;
    case "kv":
      return Array.isArray(value) && (value as KvRow[]).some((r) => r.key.trim() && r.value.trim());
    default:
      return typeof value === "string" && value.trim() !== "";
  }
}

/** True when every required field in `fields` is filled — gates the submit button. */
export function isFormComplete(fields: DdcpField[], state: DdcpFormState): boolean {
  return fields.every((f) => !f.required || isFieldFilled(f, state[f.name]));
}

function coerceScalar(type: DdcpFieldType, raw: string): unknown {
  const v = raw.trim();
  if (v === "") return undefined;
  switch (type) {
    case "number":
      return Number(v);
    case "bool":
      return v === "true";
    case "datetime": {
      const d = new Date(v);
      return Number.isNaN(d.getTime()) ? v : d.toISOString();
    }
    default:
      // text / decimal / select / batchSelect / equipmentSelect: kept verbatim as a string. Decimal
      // quantities in particular must never be parsed into a binary float (AG-15 / DATA-FR-019) — the
      // backend itself accepts these as decimal-as-string.
      return v;
  }
}

/** A bare "true"/"false"/number-looking string becomes that type; anything else stays a string. Used
 * only for the free-form key/value editor (constituent_architecture / required_controls), which has no
 * fixed schema to type each value against. */
function inferKvValue(raw: string): unknown {
  const v = raw.trim();
  if (v === "true") return true;
  if (v === "false") return false;
  if (/^-?\d+(\.\d+)?$/.test(v)) return Number(v);
  return v;
}

/** The JSON value for one field, or `undefined` if it should be omitted from the payload entirely. */
export function buildFieldValue(field: DdcpField, value: FieldValue): unknown {
  switch (field.type) {
    case "ref": {
      const v = value as RefValue;
      if (!v?.key || !v.value?.trim()) return undefined;
      return { [v.key]: v.value.trim() };
    }
    case "repeat": {
      const rows = (value as RepeatRow[] | undefined) ?? [];
      const built = rows
        .map((row) => {
          const obj: Record<string, unknown> = {};
          for (const sf of field.subFields ?? []) {
            const c = coerceScalar(sf.type, row[sf.name] ?? "");
            if (c !== undefined) obj[sf.name] = c;
          }
          return obj;
        })
        .filter((obj) => Object.keys(obj).length > 0);
      return built.length > 0 ? built : undefined;
    }
    case "kv": {
      const rows = (value as KvRow[] | undefined) ?? [];
      const obj: Record<string, unknown> = {};
      for (const r of rows) {
        const k = r.key.trim();
        if (!k) continue;
        obj[k] = inferKvValue(r.value ?? "");
      }
      // Unlike the other field types, an empty key/value editor is a meaningful value in its own
      // right — `{}` — not "nothing to send": every DDCP command with a kv field declares it as a
      // plain `dict` (required or defaulted to `{}`), never optional/nullable, so the key must always
      // be present in the payload.
      return obj;
    }
    case "boolKv": {
      const v = (value as string) ?? "";
      if (v === "" || !field.kvKey) return undefined;
      return { [field.kvKey]: v === "true" };
    }
    default:
      return coerceScalar(field.type, (value as string) ?? "");
  }
}

/** Assembles the exact JSON body the backend command expects. `skip` excludes fields that were used to
 * fill a `{param}` in the request path instead of the body. */
export function buildPayload(fields: DdcpField[], state: DdcpFormState, skip?: Set<string>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of fields) {
    if (skip?.has(f.name)) continue;
    const built = buildFieldValue(f, state[f.name]);
    if (built !== undefined) out[f.name] = built;
  }
  return out;
}
