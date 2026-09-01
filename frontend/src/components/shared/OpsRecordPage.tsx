"use client";

import { useState, type ReactNode } from "react";
import { api, ApiError, newIdempotencyKey, type Me, type MutationReceipt } from "@/lib/api";
import { useMe, useSiteId } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Icon } from "@/components/ui/Icon";
import { FactGrid } from "@/components/ui/FactGrid";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { WorkflowActionButton } from "@/components/shared/WorkflowActionButton";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";

/** A form field on a create form or a transition form. `json` fields are parsed before submit. */
export interface OpsFieldDef {
  name: string;
  label: string;
  type?: "text" | "number" | "textarea" | "json";
  hint?: string;
  required?: boolean;
  placeholder?: string;
}

export interface OpsTransitionDef<T> {
  key: string;
  label: string;
  /** true → routed through the Part 11 signature ceremony. */
  signed?: boolean;
  /** action name posted to `{detailPath}/signature-challenges` (signed) — defaults to `key`. */
  challengeAction?: string;
  variant?: "primary" | "secondary" | "ghost" | "danger" | "success";
  fields?: OpsFieldDef[];
  /** Whether to offer this transition for the loaded record. */
  show?: (record: T) => boolean;
  can?: (me: Me | null) => boolean;
  summary: ReactNode;
  /** Path segment appended to `{apiRoot}/{id}` for the mutation. Defaults to `key`. */
  pathSegment?: string;
  /** Build the mutation body from parsed field values + the record. `idempotency_key` and (for
   * signed) `challenge_id`/`reauth_password` are merged in automatically. */
  buildBody: (record: T, values: Record<string, unknown>) => Record<string, unknown>;
}

export interface OpsRecordConfig<T> {
  title: string;
  subtitle: string;
  /** Human label for the id input, e.g. "Cleaning execution ID". */
  idLabel: string;
  /** e.g. `/cleaning/v1/executions` — detail is `{apiRoot}/{id}`, mutations `{apiRoot}/{id}/{seg}`. */
  apiRoot: string;
  create?: {
    label: string;
    can: (me: Me | null) => boolean;
    /** POST target, e.g. `/cleaning/v1/executions`. */
    path: string;
    fields: OpsFieldDef[];
    /** `siteId` is the active site; returns the POST body (idempotency_key merged automatically). */
    buildBody: (values: Record<string, unknown>, siteId: string | null) => Record<string, unknown>;
  };
  stateOf: (r: T) => string;
  numberOf: (r: T) => string;
  facts: (r: T) => ReactNode;
  extra?: (r: T) => ReactNode;
  transitions: OpsTransitionDef<T>[];
}

function parseValues(fields: OpsFieldDef[], raw: Record<string, string>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of fields) {
    const v = (raw[f.name] ?? "").trim();
    if (v === "") {
      out[f.name] = null;
      continue;
    }
    if (f.type === "number") out[f.name] = Number(v);
    else if (f.type === "json") out[f.name] = JSON.parse(v);
    else out[f.name] = v;
  }
  return out;
}

function FieldInputs({
  fields,
  values,
  setValue,
}: {
  fields: OpsFieldDef[];
  values: Record<string, string>;
  setValue: (name: string, v: string) => void;
}) {
  return (
    <>
      {fields.map((f) => (
        <Field key={f.name} label={f.label} required={f.required} hint={f.hint}>
          {f.type === "textarea" || f.type === "json" ? (
            <textarea
              className="input"
              rows={f.type === "json" ? 4 : 2}
              value={values[f.name] ?? ""}
              onChange={(e) => setValue(f.name, e.target.value)}
              placeholder={f.placeholder ?? (f.type === "json" ? "{ }" : undefined)}
              spellCheck={false}
            />
          ) : (
            <Input
              type={f.type === "number" ? "number" : "text"}
              value={values[f.name] ?? ""}
              onChange={(e) => setValue(f.name, e.target.value)}
              placeholder={f.placeholder}
            />
          )}
        </Field>
      ))}
    </>
  );
}

/** The shared "look up one operations record by id, view it, drive its workflow" page — used by the
 * WP-06 cleaning / EM / sterilization / aseptic screens, none of which have a list endpoint. */
export function OpsRecordPage<T extends { id: string; version: number }>({ config }: { config: OpsRecordConfig<T> }) {
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [id, setId] = useState("");
  const [record, setRecord] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sigTransition, setSigTransition] = useState<OpsTransitionDef<T> | null>(null);
  const [sigValues, setSigValues] = useState<Record<string, string>>({});
  const [createValues, setCreateValues] = useState<Record<string, string>>({});
  const [createErr, setCreateErr] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  async function load(target = id) {
    if (!target.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setRecord(await api.get<T>(`${config.apiRoot}/${target.trim()}`));
      setId(target.trim());
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : "Lookup failed");
      setRecord(null);
    } finally {
      setLoading(false);
    }
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!config.create) return;
    setCreating(true);
    setCreateErr(null);
    try {
      const values = parseValues(config.create.fields, createValues);
      const receipt = await api.post<MutationReceipt>(config.create.path, {
        idempotency_key: newIdempotencyKey(),
        ...config.create.buildBody(values, siteId),
      });
      setCreateValues({});
      load(receipt.aggregate_id);
    } catch (err) {
      if (err instanceof SyntaxError) setCreateErr(`Invalid JSON: ${err.message}`);
      else setCreateErr(err instanceof ApiError ? `${err.code}: ${err.message}` : "Create failed");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <PageHead title={config.title} subtitle={config.subtitle} />

      {config.create && config.create.can(me) && (
        <Card pad className="mb-4">
          <CardHeader title={config.create.label} />
          <form onSubmit={create} className="grid grid-cols-2 gap-4 mt-3">
            <FieldInputs
              fields={config.create.fields}
              values={createValues}
              setValue={(n, v) => setCreateValues((c) => ({ ...c, [n]: v }))}
            />
            <div style={{ gridColumn: "1 / -1" }}>
              {createErr && <p className="error-text mb-2">{createErr}</p>}
              <Button type="submit" variant="primary" disabled={creating}>
                {creating ? "Creating…" : config.create.label}
              </Button>
            </div>
          </form>
        </Card>
      )}

      <Card pad className="mb-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            load();
          }}
          className="flex items-end gap-3"
        >
          <Field label={config.idLabel}>
            <Input value={id} onChange={(e) => setId(e.target.value)} style={{ minWidth: 320 }} />
          </Field>
          <Button type="submit" variant="secondary" disabled={loading || !id.trim()}>
            <Icon name="search" /> {loading ? "Loading…" : "Open"}
          </Button>
        </form>
        {error && <p className="error-text mt-3">{error}</p>}
      </Card>

      {record && (
        <>
          <Card pad className="mb-4">
            <div className="flex justify-between items-center mb-3">
              <span className="font-semibold flex items-center gap-3">
                {config.numberOf(record)} <WorkflowStatePill state={config.stateOf(record)} />
              </span>
            </div>
            <FactGrid>{config.facts(record)}</FactGrid>
          </Card>

          {config.extra?.(record)}

          <Card pad>
            <CardHeader title="Actions" />
            <div className="flex flex-wrap gap-2 mt-3">
              {config.transitions
                .filter((t) => (t.show ? t.show(record) : true) && (t.can ? t.can(me) : true))
                .map((t) =>
                  t.signed ? (
                    <Button
                      key={t.key}
                      variant={t.variant ?? "secondary"}
                      onClick={() => {
                        setSigValues({});
                        setSigTransition(t);
                      }}
                    >
                      {t.label}
                    </Button>
                  ) : (
                    <UnsignedTransition key={t.key} config={config} transition={t} record={record} onDone={() => load()} />
                  )
                )}
            </div>
          </Card>
        </>
      )}

      {record && sigTransition && (
        <SignatureCeremony
          open
          onClose={() => setSigTransition(null)}
          onDone={() => {
            setSigTransition(null);
            load();
          }}
          challengePath={`${config.apiRoot}/${record.id}/signature-challenges`}
          action={sigTransition.challengeAction ?? sigTransition.key}
          title={`${sigTransition.label} — ${config.numberOf(record)}`}
          summary={sigTransition.summary}
          submitVariant={sigTransition.variant === "danger" ? "danger" : sigTransition.variant === "success" ? "success" : "primary"}
          extraFields={
            sigTransition.fields && sigTransition.fields.length > 0 ? (
              <FieldInputs fields={sigTransition.fields} values={sigValues} setValue={(n, v) => setSigValues((c) => ({ ...c, [n]: v }))} />
            ) : undefined
          }
          onSign={(p) => {
            const values = parseValues(sigTransition.fields ?? [], sigValues);
            return api.post<MutationReceipt>(
              `${config.apiRoot}/${record.id}/${sigTransition.pathSegment ?? sigTransition.key}`,
              {
                idempotency_key: p.idempotency_key,
                challenge_id: p.challenge_id,
                reauth_password: p.reauth_password,
                ...sigTransition.buildBody(record, values),
              }
            );
          }}
        />
      )}
    </div>
  );
}

function UnsignedTransition<T extends { id: string; version: number }>({
  config,
  transition,
  record,
  onDone,
}: {
  config: OpsRecordConfig<T>;
  transition: OpsTransitionDef<T>;
  record: T;
  onDone: () => void;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  return (
    <WorkflowActionButton
      label={transition.label}
      title={`${transition.label} — ${config.numberOf(record)}`}
      summary={transition.summary}
      confirmLabel={transition.label}
      variant={transition.variant ?? "secondary"}
      onDone={onDone}
      extraFields={
        transition.fields && transition.fields.length > 0 ? (
          <FieldInputs fields={transition.fields} values={values} setValue={(n, v) => setValues((c) => ({ ...c, [n]: v }))} />
        ) : undefined
      }
      onConfirm={() => {
        const parsed = parseValues(transition.fields ?? [], values);
        return api.post<MutationReceipt>(`${config.apiRoot}/${record.id}/${transition.pathSegment ?? transition.key}`, {
          idempotency_key: newIdempotencyKey(),
          ...transition.buildBody(record, parsed),
        });
      }}
    />
  );
}

export { Fact, IdFact } from "@/components/ui/FactGrid";
