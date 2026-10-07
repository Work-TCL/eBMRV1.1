"use client";

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { Table } from "@/components/ui/Table";
import { StatePill } from "@/components/ui/StatePill";
import { Stepper, StepItem } from "@/components/ui/Stepper";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { Icon } from "@/components/ui/Icon";
import type { EntityOption, EntityOptionsStatus } from "@/lib/hooks";

/** Minimal RFC4180-ish line splitter -- handles a double-quoted field (so a comma or quote inside a
 * value doesn't break the column count), without pulling in a CSV parsing dependency (Document 104).
 * Good enough for the flat, scalar-only rows every bulk-import feature in this codebase uses. */
function splitCsvLine(line: string): string[] {
  const cells: string[] = [];
  let current = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"') {
        if (line[i + 1] === '"') {
          current += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        current += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      cells.push(current.trim());
      current = "";
    } else {
      current += ch;
    }
  }
  cells.push(current.trim());
  return cells;
}

function parseCsvText(text: string): { headers: string[]; rows: string[][] } {
  const lines = text
    .replace(/^﻿/, "") // strip a BOM Excel likes to add
    .trim()
    .split(/\r?\n/)
    .filter((l) => l.trim().length > 0);
  if (lines.length === 0) return { headers: [], rows: [] };
  const headers = splitCsvLine(lines[0]);
  const rows = lines.slice(1).map(splitCsvLine);
  return { headers, rows };
}

export interface CsvFieldDef {
  key: string;
  label: string;
  required?: boolean;
  /** Shown under the mapping dropdown for this field -- e.g. an allowed-value hint. */
  hint?: string;
  /** Marks this field as a reference to another entity's row (role_name, site_code,
   * equipment_class_code, product_family_code, ...), resolved by exact code/name match -- the same
   * matching the backend already does at commit time. `fetchOptions` must return `EntityOption.value`
   * equal to the exact string the backend matches on (a code or name), not a database id, so the
   * resulting mapped row value is still the plain business-code string the backend expects. Lets the
   * admin map a CSV column (auto-resolved per row), set one fixed value for every row, or assign values
   * per row/group on the "Assign values" step (checkbox-select a group of rows, apply one value to all
   * of them, repeat with a different value for the rest) -- the same picker used on single-record forms
   * either way. */
  ref?: { kind: string; fetchOptions: () => Promise<EntityOption[]> };
}

export interface CsvImportRowOutcome {
  row_index: number;
  label: string;
  ok: boolean;
  error: string | null;
}

type FieldMapping = { mode: "column"; column: string } | { mode: "fixed"; value: string } | { mode: "assign" };

type Step = "upload" | "map" | "assign" | "preview";

const linkBtnStyle: CSSProperties = {
  background: "none",
  border: "none",
  padding: 0,
  color: "var(--brand-600)",
  fontSize: "var(--fs-2)",
  textDecoration: "underline",
  cursor: "pointer",
};

/**
 * Full-page bulk-import flow (upload -> map columns -> assign per-row reference values -> preview ->
 * commit), shared across every entity that offers CSV import (users, equipment, product master, ...).
 * Lives at `/import/[entity]`, one thin per-entity wrapper per import type -- see
 * `src/components/import/*ImportPage.tsx`.
 *
 * A field flagged `ref` can be mapped three ways: from a CSV column (per-row, auto-resolved), as one
 * fixed value for the whole batch, or "assigned" -- left unresolved until the extra "Assign values" step,
 * which only appears when at least one field uses it. That step lets the admin multi-select a group of
 * rows (e.g. every row for one site) and apply one value to all of them in a single action, repeating
 * with a different value for the rest, or editing a single row's value directly -- so a 100+-row import
 * doesn't require the source file to already carry a role/site column.
 */
export function CsvImportWizard({
  description,
  /** Rendered above the file picker, e.g. a site selector that applies to every row -- something the
   * mapping step itself has no column for. Stays visible through every step. */
  extraFields,
  fields,
  sampleCsvContent,
  sampleFileName,
  /** Builds the human label shown for a row on the "Assign values" and "Preview" steps, from whatever
   * fields are already resolved (column-mapped or fixed) at that point -- assign-mode fields are still
   * blank when this runs during the assign step. Defaults to the first CSV column's raw value. */
  rowLabel,
  onCancel,
  onDone,
  onPreview,
  onCommit,
}: {
  description?: ReactNode;
  extraFields?: ReactNode;
  fields: CsvFieldDef[];
  sampleCsvContent: string;
  sampleFileName: string;
  rowLabel?: (row: Record<string, string>) => string;
  onCancel: () => void;
  onDone: () => void;
  onPreview: (rows: Record<string, string>[]) => Promise<CsvImportRowOutcome[]>;
  onCommit: (rows: Record<string, string>[]) => Promise<{ createdCount: number; summary?: string }>;
}) {
  const [step, setStep] = useState<Step>("upload");
  const [fileName, setFileName] = useState("");
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [csvDataRows, setCsvDataRows] = useState<string[][]>([]);
  const [mapping, setMapping] = useState<Record<string, FieldMapping>>({});
  // One parallel array per assign-mode field, length === csvDataRows.length -- "" means not yet assigned.
  const [assignValues, setAssignValues] = useState<Record<string, string[]>>({});
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());
  const [bulkPick, setBulkPick] = useState<Record<string, string>>({});
  const [mappedRows, setMappedRows] = useState<Record<string, string>[]>([]);
  const [outcomes, setOutcomes] = useState<CsvImportRowOutcome[] | null>(null);
  const [commitSummary, setCommitSummary] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [refOptions, setRefOptions] = useState<Record<string, EntityOption[]>>({});
  const [refStatus, setRefStatus] = useState<Record<string, EntityOptionsStatus>>({});
  // Tracks which ref fields' fetch has already been kicked off -- a ref rather than state, so marking
  // one "started" doesn't itself need a synchronous setState in the effect body below. Absence of a
  // `refStatus` entry is rendered as "loading" (see the map-step JSX), so no "loading" state write is
  // needed either; only the eventual ready/empty/error outcome is ever set.
  const startedRefFetches = useRef<Set<string>>(new Set());

  // Fetch each ref field's option list once, as soon as mapping starts -- used by the "one value for all
  // rows" picker, the per-row pickers on the assign step, and the per-sample-value match/no-match hint.
  useEffect(() => {
    if (step !== "map") return;
    for (const f of fields) {
      if (!f.ref || startedRefFetches.current.has(f.key)) continue;
      startedRefFetches.current.add(f.key);
      f.ref
        .fetchOptions()
        .then((options) => {
          setRefOptions((prev) => ({ ...prev, [f.key]: options }));
          setRefStatus((prev) => ({ ...prev, [f.key]: options.length ? "ready" : "empty" }));
        })
        .catch(() => setRefStatus((prev) => ({ ...prev, [f.key]: "error" })));
    }
  }, [step, fields]);

  function resetForNewFile() {
    setOutcomes(null);
    setCommitSummary(null);
    setError(null);
    setAssignValues({});
    setSelectedRows(new Set());
    setBulkPick({});
  }

  function handleFile(file: File) {
    setError(null);
    const reader = new FileReader();
    reader.onload = () => {
      const { headers, rows } = parseCsvText(String(reader.result ?? ""));
      if (headers.length === 0 || rows.length === 0) {
        setError("Couldn't find a header row plus at least one data row in that file.");
        return;
      }
      setFileName(file.name);
      setCsvHeaders(headers);
      setCsvDataRows(rows);
      const auto: Record<string, FieldMapping> = {};
      for (const f of fields) {
        const match = headers.find(
          (h) => h.trim().toLowerCase() === f.key.toLowerCase() || h.trim().toLowerCase() === f.label.toLowerCase()
        );
        auto[f.key] = { mode: "column", column: match ?? "" };
      }
      setMapping(auto);
      resetForNewFile();
      setStep("map");
    };
    reader.readAsText(file);
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  function fieldMapping(key: string): FieldMapping {
    return mapping[key] ?? { mode: "column", column: "" };
  }

  function setColumnMapping(key: string, column: string) {
    setMapping((prev) => ({ ...prev, [key]: { mode: "column", column } }));
  }

  function setFixedMapping(key: string, value: string) {
    setMapping((prev) => ({ ...prev, [key]: { mode: "fixed", value } }));
  }

  function setAssignMode(key: string) {
    setMapping((prev) => ({ ...prev, [key]: { mode: "assign" } }));
    setAssignValues((prev) => (prev[key] ? prev : { ...prev, [key]: csvDataRows.map(() => "") }));
  }

  /** Up to 3 distinct sample values for a mapped column, for display under its select during mapping. */
  function sampleValuesFor(column: string): string[] {
    if (!column) return [];
    const idx = csvHeaders.indexOf(column);
    if (idx === -1) return [];
    const seen = new Set<string>();
    for (const cells of csvDataRows) {
      const v = (cells[idx] ?? "").trim();
      if (v) seen.add(v);
      if (seen.size >= 3) break;
    }
    return Array.from(seen);
  }

  /** Resolves every non-assign field for every row -- assign-mode fields come out as "" until the
   * assign step fills `assignValues`. Used both to render row labels on the assign step and as the base
   * for the final `buildRows()` once assignment is complete. */
  function partialRows(): Record<string, string>[] {
    const headerIndex = new Map(csvHeaders.map((h, i) => [h, i]));
    return csvDataRows.map((cells, rowIdx) => {
      const row: Record<string, string> = {};
      for (const f of fields) {
        const m = fieldMapping(f.key);
        if (m.mode === "fixed") row[f.key] = m.value;
        else if (m.mode === "assign") row[f.key] = assignValues[f.key]?.[rowIdx] ?? "";
        else {
          const idx = m.column ? headerIndex.get(m.column) : undefined;
          row[f.key] = idx !== undefined ? cells[idx] ?? "" : "";
        }
      }
      return row;
    });
  }

  function labelForRow(row: Record<string, string>, rowIdx: number): string {
    if (rowLabel) {
      const label = rowLabel(row);
      if (label) return label;
    }
    return csvDataRows[rowIdx]?.[0] || `Row ${rowIdx + 1}`;
  }

  const assignFields = fields.filter((f) => fieldMapping(f.key).mode === "assign");

  function confirmMapping() {
    const missing = fields.filter((f) => {
      if (!f.required) return false;
      const m = fieldMapping(f.key);
      if (m.mode === "assign") return false; // checked on the assign step instead
      return m.mode === "column" ? !m.column : !m.value;
    });
    if (missing.length > 0) {
      setError(`Pick a column or value for: ${missing.map((f) => f.label).join(", ")}`);
      return;
    }
    setError(null);
    if (assignFields.length > 0) {
      setStep("assign");
    } else {
      finishMapping();
    }
  }

  function setRowAssignValue(key: string, rowIdx: number, value: string) {
    setAssignValues((prev) => {
      const arr = (prev[key] ?? csvDataRows.map(() => "")).slice();
      arr[rowIdx] = value;
      return { ...prev, [key]: arr };
    });
  }

  function toggleRowSelected(rowIdx: number) {
    setSelectedRows((prev) => {
      const next = new Set(prev);
      if (next.has(rowIdx)) next.delete(rowIdx);
      else next.add(rowIdx);
      return next;
    });
  }

  function toggleSelectAll() {
    setSelectedRows((prev) => (prev.size === csvDataRows.length ? new Set() : new Set(csvDataRows.map((_, i) => i))));
  }

  function applyBulkPick(key: string) {
    const value = bulkPick[key];
    if (!value || selectedRows.size === 0) return;
    setAssignValues((prev) => {
      const arr = (prev[key] ?? csvDataRows.map(() => "")).slice();
      for (const idx of selectedRows) arr[idx] = value;
      return { ...prev, [key]: arr };
    });
  }

  function confirmAssign() {
    const unassignedCounts = assignFields
      .filter((f) => f.required)
      .map((f) => ({ field: f, count: (assignValues[f.key] ?? []).filter((v) => !v).length }))
      .filter((x) => x.count > 0);
    if (unassignedCounts.length > 0) {
      setError(
        unassignedCounts.map((x) => `${x.count} row(s) still need a ${x.field.label}`).join("; ")
      );
      return;
    }
    finishMapping();
  }

  function finishMapping() {
    setMappedRows(partialRows());
    setError(null);
    setOutcomes(null);
    setCommitSummary(null);
    setStep("preview");
  }

  async function runPreview() {
    setBusy(true);
    setError(null);
    try {
      setOutcomes(await onPreview(mappedRows));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to validate rows");
    } finally {
      setBusy(false);
    }
  }

  // Run validation as soon as the preview step is reached, so the admin sees row-by-row status
  // immediately instead of needing to click a button first -- the "Preview" button then only exists to
  // retry after a transient failure.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- runPreview's first line is setBusy(true); the real work after it is async.
    if (step === "preview" && outcomes === null && !busy) runPreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- fires once per arrival at "preview"; re-running on every mappedRows/busy change would refire mid-check.
  }, [step]);

  async function runCommit() {
    setBusy(true);
    setError(null);
    try {
      const result = await onCommit(mappedRows);
      setCommitSummary(result.summary ?? `Created ${result.createdCount} row(s).`);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to import");
    } finally {
      setBusy(false);
    }
  }

  const allValid = outcomes !== null && outcomes.length > 0 && outcomes.every((o) => o.ok);
  const sampleHref = `data:text/csv;charset=utf-8,${encodeURIComponent(sampleCsvContent)}`;

  const stepOrder: Step[] = assignFields.length > 0 ? ["upload", "map", "assign", "preview"] : ["upload", "map", "preview"];
  const stepIndex = stepOrder.indexOf(step);

  const assignPartialRows = step === "assign" ? partialRows() : [];

  return (
    <Card pad>
      <Stepper horizontal>
        <StepItem state={stepIndex === 0 ? "current" : "completed"} number={1} title="Upload" />
        <StepItem
          state={stepIndex === 1 ? "current" : stepIndex > 1 ? "completed" : "pending"}
          number={2}
          title="Map columns"
        />
        {assignFields.length > 0 && (
          <StepItem
            state={step === "assign" ? "current" : stepIndex > stepOrder.indexOf("assign") ? "completed" : "pending"}
            number={3}
            title="Assign values"
          />
        )}
        <StepItem state={step === "preview" ? "current" : "pending"} number={assignFields.length > 0 ? 4 : 3} title="Preview &amp; import" />
      </Stepper>

      {description && <p className="hint mb-3 mt-3">{description}</p>}
      {extraFields}
      {step === "upload" && (
        <div className="flex items-center justify-between gap-3 mb-3">
          <p className="hint" style={{ margin: 0 }}>
            Upload your own export — you&rsquo;ll match its columns to the right fields next, in whatever
            order it already has them.
          </p>
          {/* A real <a download> rather than the Button/LinkButton components: Button renders a plain
              <button> (no href at all) and LinkButton's href goes through Next's client-side router,
              neither of which can trigger a browser file download from a data: URI -- only a native
              anchor's `download` attribute does that. Styled with the same .btn classes those components
              apply, so it still looks and behaves like any other secondary button in the app. */}
          <a href={sampleHref} download={sampleFileName} className="btn btn-secondary btn-sm" style={{ whiteSpace: "nowrap", flexShrink: 0 }}>
            <Icon name="download" /> Download sample CSV
          </a>
        </div>
      )}

      {step === "upload" && (
        <div
          className="file-dropzone"
          data-drag-over={dragOver}
          role="button"
          tabIndex={0}
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const file = e.dataTransfer.files?.[0];
            if (file) handleFile(file);
          }}
        >
          <Icon name="upload" />
          <p className="file-dropzone-title">Click to choose a file, or drag and drop it here</p>
          <p className="hint">A header row plus one row per record. Comma-separated (.csv).</p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            onChange={onFileChange}
            style={{ display: "none" }}
          />
        </div>
      )}

      {step !== "upload" && (
        <p className="fs-2 text-muted mb-3">
          {fileName} — {csvDataRows.length} row{csvDataRows.length === 1 ? "" : "s"} found.{" "}
          <button
            type="button"
            style={linkBtnStyle}
            onClick={() => {
              setStep("upload");
              resetForNewFile();
            }}
          >
            Choose a different file
          </button>
        </p>
      )}

      {step === "map" && (
        <div className="flex flex-col gap-3 mb-3">
          {fields.map((f) => {
            const m = fieldMapping(f.key);
            const status = f.ref ? refStatus[f.key] ?? "loading" : undefined;
            const options = f.ref ? refOptions[f.key] ?? [] : [];
            const samples = m.mode === "column" ? sampleValuesFor(m.column) : [];
            return (
              <div key={f.key} className="card" style={{ padding: "12px 14px" }}>
                <div className="flex items-start justify-between gap-3">
                  <div style={{ flex: 1 }}>
                    {m.mode === "column" ? (
                      <Field label={f.label + (f.required ? " (required)" : " (optional)")} hint={f.hint}>
                        <Select value={m.column} onChange={(e) => setColumnMapping(f.key, e.target.value)}>
                          <option value="">— Not in this file —</option>
                          {csvHeaders.map((h) => (
                            <option key={h} value={h}>
                              {h}
                            </option>
                          ))}
                        </Select>
                      </Field>
                    ) : m.mode === "fixed" ? (
                      <EntityPickerField
                        label={f.label + (f.required ? " (required)" : " (optional)")}
                        hint={f.hint}
                        value={m.value}
                        onChange={(value) => setFixedMapping(f.key, value)}
                        options={options}
                        status={status ?? "loading"}
                        kind={f.ref?.kind ?? "value"}
                      />
                    ) : (
                      <Field label={f.label + (f.required ? " (required)" : " (optional)")} hint={f.hint}>
                        <p className="fs-2 text-muted" style={{ margin: 0, padding: "8px 0" }}>
                          Assigned per row on the next step — you&rsquo;ll pick which rows get which {f.ref?.kind ?? "value"}.
                        </p>
                      </Field>
                    )}
                  </div>
                  {f.ref && (
                    <div className="flex gap-1" style={{ marginTop: 28, flexShrink: 0 }}>
                      <Button
                        type="button"
                        variant={m.mode === "column" ? "primary" : "secondary"}
                        size="sm"
                        style={{ whiteSpace: "nowrap" }}
                        onClick={() => setColumnMapping(f.key, "")}
                      >
                        From CSV column
                      </Button>
                      <Button
                        type="button"
                        variant={m.mode === "fixed" ? "primary" : "secondary"}
                        size="sm"
                        style={{ whiteSpace: "nowrap" }}
                        onClick={() => setFixedMapping(f.key, "")}
                      >
                        Same for every row
                      </Button>
                      <Button
                        type="button"
                        variant={m.mode === "assign" ? "primary" : "secondary"}
                        size="sm"
                        style={{ whiteSpace: "nowrap" }}
                        onClick={() => setAssignMode(f.key)}
                      >
                        Assign per row
                      </Button>
                    </div>
                  )}
                </div>
                {m.mode === "column" && samples.length > 0 && (
                  <p className="fs-1 text-muted mt-1">
                    Sample values: {samples.map((v, i) => (
                      <span key={v}>
                        {i > 0 && ", "}
                        {v}
                        {f.ref && status === "ready" && (
                          <span style={{ color: options.some((o) => o.value.toLowerCase() === v.toLowerCase()) ? "var(--status-success-solid, green)" : "var(--status-critical-solid, crimson)" }}>
                            {" "}
                            {options.some((o) => o.value.toLowerCase() === v.toLowerCase()) ? "(matches)" : "(no match — row will fail)"}
                          </span>
                        )}
                      </span>
                    ))}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {step === "assign" && (
        <div className="mb-3">
          <p className="hint mb-2">
            Select a group of rows below, pick a value for each field in the toolbar, then apply it to
            just that group. Repeat with a different value for the rest, or edit a single row&rsquo;s
            dropdown directly.
          </p>
          <div className="card flex flex-wrap items-end gap-3 mb-2" style={{ padding: "10px 14px" }}>
            <span className="fs-2" style={{ fontWeight: 600 }}>
              {selectedRows.size} row{selectedRows.size === 1 ? "" : "s"} selected
            </span>
            {assignFields.map((f) => {
              const status = f.ref ? refStatus[f.key] ?? "loading" : "ready";
              const options = refOptions[f.key] ?? [];
              return (
                <div key={f.key} className="flex items-end gap-1">
                  <Field label={f.label}>
                    <Select
                      value={bulkPick[f.key] ?? ""}
                      onChange={(e) => setBulkPick((prev) => ({ ...prev, [f.key]: e.target.value }))}
                      disabled={status !== "ready"}
                    >
                      <option value="">{status === "loading" ? "Loading…" : "— Choose —"}</option>
                      {options.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    disabled={!bulkPick[f.key] || selectedRows.size === 0}
                    onClick={() => applyBulkPick(f.key)}
                  >
                    Apply to selected
                  </Button>
                </div>
              );
            })}
            {selectedRows.size > 0 && (
              <Button type="button" variant="secondary" size="sm" onClick={() => setSelectedRows(new Set())}>
                Clear selection
              </Button>
            )}
          </div>
          <Table>
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    checked={selectedRows.size === csvDataRows.length && csvDataRows.length > 0}
                    onChange={toggleSelectAll}
                    aria-label="Select all rows"
                  />
                </th>
                <th>Row</th>
                <th>Record</th>
                {assignFields.map((f) => (
                  <th key={f.key}>{f.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {assignPartialRows.map((row, idx) => (
                <tr key={idx}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selectedRows.has(idx)}
                      onChange={() => toggleRowSelected(idx)}
                      aria-label={`Select row ${idx + 1}`}
                    />
                  </td>
                  <td>{idx + 1}</td>
                  <td>{labelForRow(row, idx)}</td>
                  {assignFields.map((f) => {
                    const options = refOptions[f.key] ?? [];
                    const status = refStatus[f.key] ?? "loading";
                    return (
                      <td key={f.key}>
                        <Select
                          value={assignValues[f.key]?.[idx] ?? ""}
                          onChange={(e) => setRowAssignValue(f.key, idx, e.target.value)}
                          disabled={status !== "ready"}
                        >
                          <option value="">{status === "loading" ? "Loading…" : "— Not set —"}</option>
                          {options.map((o) => (
                            <option key={o.value} value={o.value}>
                              {o.label}
                            </option>
                          ))}
                        </Select>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}

      {step === "preview" && (
        <div className="mb-3">
          <Table>
            <thead>
              <tr>
                <th>Row</th>
                {fields.map((f) => (
                  <th key={f.key}>{f.label}</th>
                ))}
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {mappedRows.map((row, idx) => {
                const outcome = outcomes?.find((o) => o.row_index === idx);
                return (
                  <tr key={idx}>
                    <td>{idx + 1}</td>
                    {fields.map((f) => (
                      <td key={f.key}>{row[f.key] || <span className="text-muted">—</span>}</td>
                    ))}
                    <td>
                      {!outcomes ? (
                        <StatePill state="stale" icon="clock">
                          Checking…
                        </StatePill>
                      ) : outcome?.ok ? (
                        <StatePill state="accepted" icon="check-circle">
                          OK
                        </StatePill>
                      ) : (
                        <StatePill state="failed" icon="x">
                          {outcome?.error ?? "Failed"}
                        </StatePill>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        </div>
      )}

      {commitSummary && <p className="mb-3">{commitSummary}</p>}
      {error && <p className="error-text mb-3">{error}</p>}

      <div className="flex justify-between gap-3 mt-4">
        <Button
          type="button"
          variant="secondary"
          onClick={() => {
            if (step === "assign") setStep("map");
            else if (step === "preview" && assignFields.length > 0) setStep("assign");
            else if (step === "preview") setStep("map");
            else onCancel();
          }}
        >
          {step === "upload" ? "Cancel" : "Back"}
        </Button>
        <div className="flex gap-2">
          {step === "map" && (
            <Button type="button" variant="primary" onClick={confirmMapping}>
              Continue
            </Button>
          )}
          {step === "assign" && (
            <Button type="button" variant="primary" onClick={confirmAssign}>
              Continue
            </Button>
          )}
          {step === "preview" && (
            <>
              <Button type="button" variant="secondary" onClick={runPreview} disabled={busy}>
                {busy ? "Checking…" : "Re-check rows"}
              </Button>
              <Button type="button" variant="primary" onClick={runCommit} disabled={busy || !allValid}>
                {busy ? "Importing…" : `Import ${mappedRows.length} row(s)`}
              </Button>
            </>
          )}
        </div>
      </div>
    </Card>
  );
}
