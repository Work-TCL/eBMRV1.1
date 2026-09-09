"use client";

import { useState, type CSSProperties } from "react";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import type { EntityOption, EntityOptionsStatus } from "@/lib/hooks";

const linkBtnStyle: CSSProperties = {
  background: "none",
  border: "none",
  padding: 0,
  color: "var(--brand-600)",
  fontSize: "var(--fs-2)",
  cursor: "pointer",
  textDecoration: "underline",
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
};

export interface RepeatSubField {
  name: string;
  label: string;
  /** "materialLotSelect" renders a released-material-lot dropdown with the same manual-ID fallback as
   * `EntityPickerField`, compacted to fit this component's dense row layout — used by a load item's
   * "Item reference" (Document 42), which is most often a material lot, but stays free text for
   * non-lot loads (garments, filters, …) via the fallback. */
  type?: "text" | "number" | "select" | "bool" | "materialLotSelect";
  required?: boolean;
  placeholder?: string;
  options?: { value: string; label: string }[];
  default?: string;
}
export type RepeatRow = Record<string, string>;
export interface KvRow {
  key: string;
  value: string;
}

function SubFieldControl({
  field,
  value,
  onChange,
  materialLotOptions,
  materialLotOptionsStatus,
}: {
  field: RepeatSubField;
  value: string;
  onChange: (value: string) => void;
  /** Backs "materialLotSelect" — omitted for every other sub-field type. */
  materialLotOptions?: EntityOption[];
  materialLotOptionsStatus?: EntityOptionsStatus;
}) {
  const [manual, setManual] = useState(false);
  const labelRow = (
    <label className="hint" style={{ display: "block", marginBottom: 4 }}>
      {field.label} {field.required && <span style={{ color: "var(--status-critical-solid)" }}>*</span>}
    </label>
  );
  if (field.type === "materialLotSelect") {
    const status = materialLotOptionsStatus ?? "empty";
    const options = materialLotOptions ?? [];
    const useManual = manual || status === "error" || status === "empty";
    if (useManual) {
      return (
        <div>
          {labelRow}
          <Input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder={field.placeholder ?? "e.g. LOT-DEV-2601, or a garment/filter reference"} />
          {status === "ready" && (
            <button type="button" style={{ ...linkBtnStyle, marginTop: 4, fontSize: "var(--fs-1)" }} onClick={() => setManual(false)}>
              Choose a lot instead
            </button>
          )}
        </div>
      );
    }
    if (status === "loading") {
      return (
        <div>
          {labelRow}
          <Select disabled>
            <option>Loading material lots…</option>
          </Select>
        </div>
      );
    }
    return (
      <div>
        {labelRow}
        <Select value={value} onChange={(e) => onChange(e.target.value)}>
 <option value="">Select a material lot</option>
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
        <button type="button" style={{ ...linkBtnStyle, marginTop: 4, fontSize: "var(--fs-1)" }} onClick={() => setManual(true)}>
          Not a lot? Enter reference manually
        </button>
      </div>
    );
  }
  if (field.type === "select") {
    return (
      <div>
        {labelRow}
        <Select value={value} onChange={(e) => onChange(e.target.value)}>
 <option value="">Select</option>
          {(field.options ?? []).map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
      </div>
    );
  }
  if (field.type === "bool") {
    return (
      <div>
        {labelRow}
        <Select value={value} onChange={(e) => onChange(e.target.value)}>
 <option value=""></option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </Select>
      </div>
    );
  }
  return (
    <div>
      {labelRow}
      <Input type={field.type === "number" ? "number" : "text"} value={value} onChange={(e) => onChange(e.target.value)} placeholder={field.placeholder} />
    </div>
  );
}

/** Replaces a JSON array (one structured row per entry — samples, requirements, line items, …) with
 * Add/Remove rows of plain fields. Used wherever a field would otherwise need raw `[{...}, {...}]`
 * JSON entry (spec sections 5–6's worked example). */
export function RepeatableRows({
  label,
  required,
  hint,
  itemLabel,
  subFields,
  value,
  onChange,
  materialLotOptions,
  materialLotOptionsStatus,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  itemLabel?: string;
  subFields: RepeatSubField[];
  value: RepeatRow[];
  onChange: (value: RepeatRow[]) => void;
  /** Backs any "materialLotSelect" sub-field — omitted when no sub-field uses that type. */
  materialLotOptions?: EntityOption[];
  materialLotOptionsStatus?: EntityOptionsStatus;
}) {
  const rows = value ?? [];
  const item = itemLabel ?? label;

  function addRow() {
    const blank: RepeatRow = {};
    for (const sf of subFields) blank[sf.name] = sf.default ?? "";
    onChange([...rows, blank]);
  }
  function updateRow(i: number, name: string, v: string) {
    onChange(rows.map((r, idx) => (idx === i ? { ...r, [name]: v } : r)));
  }
  function removeRow(i: number) {
    onChange(rows.filter((_, idx) => idx !== i));
  }

  return (
    <div className="field">
      <label className="label">
        {label} {required && <span className="req">*</span>}
      </label>
      {hint && <p className="hint mb-2">{hint}</p>}
      {rows.map((row, i) => (
        <div key={i} className="sig-block mb-3">
          <div className="flex items-center justify-between mb-2">
            <span className="fs-2 font-semibold text-muted">
              {item} {i + 1}
            </span>
            <button type="button" style={linkBtnStyle} onClick={() => removeRow(i)} aria-label={`Remove ${item} ${i + 1}`}>
              <Icon name="x" /> Remove
            </button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {subFields.map((sf) => (
              <SubFieldControl
                key={sf.name} field={sf} value={row[sf.name] ?? ""} onChange={(v) => updateRow(i, sf.name, v)}
                materialLotOptions={materialLotOptions} materialLotOptionsStatus={materialLotOptionsStatus}
              />
            ))}
          </div>
        </div>
      ))}
      <Button type="button" variant="secondary" size="sm" onClick={addRow}>
        <Icon name="plus" /> Add {item.toLowerCase()}
      </Button>
      {rows.length === 0 && required && (
        <p className="error-text mt-2">
          <Icon name="alert-circle" /> Add at least one {item.toLowerCase()}.
        </p>
      )}
    </div>
  );
}

/** Replaces a free-form JSON object (no fixed schema) with plain "setting name" / "value" rows.
 * Values are typed automatically (true/false/number/text) when the payload is built. */
export function KeyValueRows({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint?: string;
  value: KvRow[];
  onChange: (value: KvRow[]) => void;
}) {
  const rows = value ?? [];

  function update(i: number, patch: Partial<KvRow>) {
    onChange(rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }
  function add() {
    onChange([...rows, { key: "", value: "" }]);
  }
  function remove(i: number) {
    onChange(rows.filter((_, idx) => idx !== i));
  }

  return (
    <div className="field">
      <label className="label">{label}</label>
      {hint && <p className="hint mb-2">{hint}</p>}
      {rows.map((row, i) => (
        <div key={i} className="flex flex-wrap gap-2 mb-2 items-center">
          <Input placeholder="Setting name" value={row.key} onChange={(e) => update(i, { key: e.target.value })} style={{ flex: "1 1 140px", minWidth: 0 }} />
          <Input placeholder="Value" value={row.value} onChange={(e) => update(i, { value: e.target.value })} style={{ flex: "2 1 140px", minWidth: 0 }} />
          <button type="button" style={linkBtnStyle} onClick={() => remove(i)} aria-label={`Remove setting ${i + 1}`}>
            <Icon name="x" />
          </button>
        </div>
      ))}
      <Button type="button" variant="secondary" size="sm" onClick={add}>
        <Icon name="plus" /> Add setting
      </Button>
    </div>
  );
}

/** Replaces a plain JSON string array (`["a", "b"]` — no per-item structure) with Add/Remove rows of a
 * single text input each. Used where the backend field is `list[str]`, not `list[dict]` (see
 * `RepeatableRows` for the latter). */
export function StringListRows({
  label,
  required,
  hint,
  itemLabel,
  placeholder,
  value,
  onChange,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  itemLabel?: string;
  placeholder?: string;
  value: string[];
  onChange: (value: string[]) => void;
}) {
  const rows = value ?? [];
  const item = itemLabel ?? label;

  return (
    <div className="field">
      <label className="label">
        {label} {required && <span className="req">*</span>}
      </label>
      {hint && <p className="hint mb-2">{hint}</p>}
      {rows.map((row, i) => (
        <div key={i} className="flex gap-2 mb-2 items-center">
          <Input
            value={row}
            placeholder={placeholder}
            onChange={(e) => onChange(rows.map((r, idx) => (idx === i ? e.target.value : r)))}
            style={{ flex: 1 }}
          />
          <button
            type="button"
            style={linkBtnStyle}
            onClick={() => onChange(rows.filter((_, idx) => idx !== i))}
            aria-label={`Remove ${item} ${i + 1}`}
          >
            <Icon name="x" />
          </button>
        </div>
      ))}
      <Button type="button" variant="secondary" size="sm" onClick={() => onChange([...rows, ""])}>
        <Icon name="plus" /> Add {item.toLowerCase()}
      </Button>
      {rows.length === 0 && required && (
        <p className="error-text mt-2">
          <Icon name="alert-circle" /> Add at least one {item.toLowerCase()}.
        </p>
      )}
    </div>
  );
}

/** `{key: value}` from key/value rows, typing each value automatically. Always returns an object (even
 * `{}`) — a free-form settings field with nothing entered is still a meaningful, present value. */
export function buildKvObject(rows: KvRow[]): Record<string, unknown> {
  const obj: Record<string, unknown> = {};
  for (const r of rows ?? []) {
    const k = r.key.trim();
    if (!k) continue;
    const v = r.value.trim();
    obj[k] = v === "true" ? true : v === "false" ? false : /^-?\d+(\.\d+)?$/.test(v) ? Number(v) : v;
  }
  return obj;
}

/** Trims and drops empty rows from a `StringListRows` value. */
export function buildStringList(rows: string[]): string[] {
  return (rows ?? []).map((r) => r.trim()).filter((r) => r !== "");
}

function coerceSubField(field: RepeatSubField, raw: string): unknown {
  const v = raw.trim();
  if (v === "") return undefined;
  if (field.type === "number") return Number(v);
  if (field.type === "bool") return v === "true";
  return v;
}

/** An array of plain objects from repeatable rows, dropping any row left entirely empty. */
export function buildRepeatArray(subFields: RepeatSubField[], rows: RepeatRow[]): Record<string, unknown>[] {
  return (rows ?? [])
    .map((row) => {
      const obj: Record<string, unknown> = {};
      for (const sf of subFields) {
        const c = coerceSubField(sf, row[sf.name] ?? "");
        if (c !== undefined) obj[sf.name] = c;
      }
      return obj;
    })
    .filter((obj) => Object.keys(obj).length > 0);
}
