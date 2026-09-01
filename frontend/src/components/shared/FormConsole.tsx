"use client";

import { useState } from "react";
import { api, ApiError, newIdempotencyKey, type MutationReceipt } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { JsonPanel } from "@/components/ui/JsonPanel";

export interface FormField {
  name: string;
  label: string;
  type?: "text" | "number" | "date" | "datetime" | "select" | "textarea" | "json" | "bool";
  required?: boolean;
  hint?: string;
  placeholder?: string;
  options?: { value: string; label: string }[];
  /** Seed value. */
  default?: string;
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

/** Names referenced as `{name}` in a path — filled from fields, not sent in the body. */
function pathParams(path: string): Set<string> {
  return new Set(Array.from(path.matchAll(/\{(\w+)\}/g), (m) => m[1]));
}

function coerce(field: FormField, raw: string): unknown {
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
  const [values, setValues] = useState<Record<string, string>>(() => seed(ops[0]));
  const [jsonBody, setJsonBody] = useState(ops[0]?.template ?? "{\n  \n}");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(undefined);

  function seed(o: FormOp): Record<string, string> {
    const s: Record<string, string> = {};
    for (const f of o.fields ?? []) if (f.default !== undefined) s[f.name] = f.default;
    return s;
  }

  function selectOp(next: number) {
    setIdx(next);
    setValues(seed(ops[next]));
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
      const params = pathParams(op.path);
      const filledPath = op.path.replace(/\{(\w+)\}/g, (_, name) => encodeURIComponent((values[name] ?? "").trim()));
      const url = `${root}/${filledPath}`;
      if (op.method === "GET") {
        setResult(await api.get<unknown>(url));
      } else {
        let body: Record<string, unknown> = {};
        if (op.fields) {
          for (const f of op.fields) {
            if (params.has(f.name)) continue; // used in the path, not the body
            const c = coerce(f, values[f.name] ?? "");
            if (c !== null) body[f.name] = c;
          }
        } else {
          body = jsonBody.trim() ? JSON.parse(jsonBody) : {};
        }
        setResult(await api.post<MutationReceipt>(url, { idempotency_key: newIdempotencyKey(), ...body }));
      }
    } catch (err) {
      if (err instanceof SyntaxError) setError(`Invalid JSON: ${err.message}`);
      else setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  const missingRequired =
    op.fields?.some((f) => f.required && !(values[f.name] ?? "").trim()) ?? false;

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
          <div className="grid grid-cols-2 gap-4">
            {op.fields.map((f) => (
              <Field key={f.name} label={f.label} required={f.required} hint={f.hint}>
                {f.type === "select" ? (
                  <Select value={values[f.name] ?? ""} onChange={(e) => setValues((c) => ({ ...c, [f.name]: e.target.value }))}>
                    <option value="">—</option>
                    {(f.options ?? []).map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </Select>
                ) : f.type === "bool" ? (
                  <Select value={values[f.name] ?? ""} onChange={(e) => setValues((c) => ({ ...c, [f.name]: e.target.value }))}>
                    <option value="">—</option>
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
            ))}
          </div>
        ) : op.method === "GET" ? null : (
          <Field label="Payload (JSON)" hint="This operation has a nested payload — see the API contract.">
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
