"use client";

import { useEffect, useState, type ReactNode } from "react";
import { api, ApiError, newIdempotencyKey, type Me, type MutationReceipt } from "@/lib/api";
import { useEntityOptions, useMe, useSiteId, type EntityOptionsStatus } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card, CardHeader } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Icon } from "@/components/ui/Icon";
import { FactGrid } from "@/components/ui/FactGrid";
import { Banner } from "@/components/ui/Banner";
import { WorkflowStatePill } from "@/components/ui/StatePill";
import { WorkflowActionButton } from "@/components/shared/WorkflowActionButton";
import { SignatureCeremony } from "@/components/shared/SignatureCeremony";
import { EntityPickerField } from "@/components/shared/EntityPicker";
import { RepeatableRows, KeyValueRows, buildKvObject, buildRepeatArray, type RepeatRow, type KvRow, type RepeatSubField } from "@/components/shared/RepeatableFields";

/** A form field on a create form or a transition form. `json` fields are parsed before submit;
 * `select`/`bool` render a dropdown instead of free text; `batchSelect`/`equipmentSelect` render a
 * picker instead of a raw id; `repeat`/`kv` replace a JSON array/object with structured rows (additive
 * — every pre-existing type behaves exactly as before). */
export interface OpsFieldDef {
  name: string;
  label: string;
  type?: "text" | "number" | "date" | "textarea" | "json" | "select" | "bool" | "batchSelect" | "equipmentSelect" | "areaSelect" | "userSelect" | "materialSelect" | "supplierSelect" | "sterilizationProfileSelect" | "asepticProfileSelect" | "cleaningProcedureVersionSelect" | "cleaningProcedureCodeSelect" | "batchStepSelect" | "repeat" | "kv";
  /** "batchStepSelect" only — the name of the sibling field on the same form whose current value is the
   * batch id to fetch steps for (e.g. "batch_id"). Steps reload whenever that field's value changes. */
  batchIdField?: string;
  hint?: string;
  required?: boolean;
  placeholder?: string;
  /** "select" only. */
  options?: { value: string; label: string }[];
  /** "repeat" only — the shape of each row. */
  subFields?: RepeatSubField[];
  /** "repeat" only — used in "Add …" / "Remove …" text. Defaults to `label`. */
  itemLabel?: string;
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

function parseValues(
  fields: OpsFieldDef[],
  raw: Record<string, string>,
  complex: Record<string, RepeatRow[] | KvRow[]> = {}
): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of fields) {
    if (f.type === "repeat") {
      out[f.name] = buildRepeatArray(f.subFields ?? [], (complex[f.name] as RepeatRow[]) ?? []);
      continue;
    }
    if (f.type === "kv") {
      out[f.name] = buildKvObject((complex[f.name] as KvRow[]) ?? []);
      continue;
    }
    const v = (raw[f.name] ?? "").trim();
    if (v === "") {
      out[f.name] = null;
      continue;
    }
    if (f.type === "number") out[f.name] = Number(v);
    else if (f.type === "json") out[f.name] = JSON.parse(v);
    else if (f.type === "date") out[f.name] = new Date(v).toISOString();
    else out[f.name] = v;
  }
  return out;
}

/** A "batch step" picker scoped to a sibling field's current batch id — same cascading shape as
 * FormConsole.tsx's own `BatchStepOwnerPicker`, adapted here since `OpsRecordPage`'s field vocabulary
 * had no record-scoped (not globally-fetched) picker type before this (e.g. aseptic operation create's
 * "Batch step ID", previously free text with no way to discover a real one even though "Batch" is right
 * above it on the same form). Falls back to manual entry the same way every other picker type does. */
function BatchStepSelectField({
  label,
  required,
  hint,
  value,
  onChange,
  batchId,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
  batchId: string;
}) {
  const [manual, setManual] = useState(false);
  const [steps, setSteps] = useState<{ step_id: string; recipe_step_code: string }[]>([]);
  const [status, setStatus] = useState<EntityOptionsStatus>("empty");

  useEffect(() => {
    // No reset-to-empty branch needed when `batchId` is falsy: the render below already checks
    // `!batchId` directly (not derived from `status`), so stale `steps`/`status` from a previously
    // selected batch are simply never shown while no batch is selected -- avoids a synchronous setState
    // in the effect body for a case the render path already handles correctly on its own.
    if (!batchId) return;
    let cancelled = false;
    api
      .get<{ steps: { step_id: string; recipe_step_code: string }[] }>(`/batches/v1/${batchId}/execution-view`)
      .then((res) => {
        if (cancelled) return;
        setSteps(res.steps);
        setStatus(res.steps.length ? "ready" : "empty");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [batchId]);

  if (manual || !batchId || status === "error") {
    return (
      <Field label={label} required={required} hint={hint ?? (!batchId ? "Select a batch above first." : undefined)}>
        <Input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder="Batch step ID" />
        {batchId && status !== "error" && (
          <button
            type="button"
            style={{ background: "none", border: "none", padding: 0, color: "var(--brand-600)", fontSize: "var(--fs-2)", cursor: "pointer", textDecoration: "underline", marginTop: 6 }}
            onClick={() => setManual(false)}
          >
            Pick a batch step instead
          </button>
        )}
      </Field>
    );
  }

  return (
    <Field label={label} required={required} hint={hint}>
      <Select value={value} onChange={(e) => onChange(e.target.value)} disabled={status === "loading"}>
        <option value="">{status === "loading" ? "Loading steps…" : "Select a step"}</option>
        {steps.map((s) => (
          <option key={s.step_id} value={s.step_id}>
            {s.recipe_step_code}
          </option>
        ))}
      </Select>
      <button
        type="button"
        style={{ background: "none", border: "none", padding: 0, color: "var(--brand-600)", fontSize: "var(--fs-2)", cursor: "pointer", textDecoration: "underline", marginTop: 6 }}
        onClick={() => setManual(true)}
      >
        Enter the step ID manually
      </button>
    </Field>
  );
}

function FieldInputs({
  fields,
  values,
  setValue,
  complexValues,
  setComplexValue,
}: {
  fields: OpsFieldDef[];
  values: Record<string, string>;
  setValue: (name: string, v: string) => void;
  complexValues?: Record<string, RepeatRow[] | KvRow[]>;
  setComplexValue?: (name: string, v: RepeatRow[] | KvRow[]) => void;
}) {
  const entities = useEntityOptions();
  return (
    <>
      {fields.map((f) => {
        if (f.type === "repeat") {
          return (
            <div key={f.name} style={{ gridColumn: "1 / -1" }}>
              <RepeatableRows
                label={f.label}
                required={f.required}
                hint={f.hint}
                itemLabel={f.itemLabel}
                subFields={f.subFields ?? []}
                value={(complexValues?.[f.name] as RepeatRow[]) ?? []}
                onChange={(rows) => setComplexValue?.(f.name, rows)}
                materialOptions={entities.materials}
                materialOptionsStatus={entities.materialsStatus}
                materialLotOptions={entities.materialLotCodes}
                materialLotOptionsStatus={entities.materialLotCodesStatus}
                userOptions={entities.users}
                userOptionsStatus={entities.usersStatus}
                equipmentOptions={entities.equipment}
                equipmentOptionsStatus={entities.equipmentStatus}
                areaOptions={entities.areas}
                areaOptionsStatus={entities.areasStatus}
              />
            </div>
          );
        }
        if (f.type === "kv") {
          return (
            <div key={f.name} style={{ gridColumn: "1 / -1" }}>
              <KeyValueRows
                label={f.label}
                hint={f.hint}
                value={(complexValues?.[f.name] as KvRow[]) ?? []}
                onChange={(rows) => setComplexValue?.(f.name, rows)}
              />
            </div>
          );
        }
        if (f.type === "batchSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.batches} status={entities.batchesStatus} kind="batch"
            />
          );
        }
        if (f.type === "equipmentSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.equipment} status={entities.equipmentStatus} kind="equipment asset"
            />
          );
        }
        if (f.type === "areaSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.areas} status={entities.areasStatus} kind="equipment area"
            />
          );
        }
        if (f.type === "userSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.users} status={entities.usersStatus} kind="user"
            />
          );
        }
        if (f.type === "materialSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.materials} status={entities.materialsStatus} kind="material"
            />
          );
        }
        if (f.type === "supplierSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.suppliers} status={entities.suppliersStatus} kind="supplier"
            />
          );
        }
        if (f.type === "sterilizationProfileSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.sterilizationProfiles} status={entities.sterilizationProfilesStatus}
              kind="sterilization/CIP-SIP profile version"
            />
          );
        }
        if (f.type === "asepticProfileSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.asepticProfiles} status={entities.asepticProfilesStatus}
              kind="aseptic process profile version"
            />
          );
        }
        if (f.type === "cleaningProcedureVersionSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.cleaningProcedureVersions} status={entities.cleaningProcedureVersionsStatus}
              kind="cleaning procedure version"
            />
          );
        }
        if (f.type === "cleaningProcedureCodeSelect") {
          return (
            <EntityPickerField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              options={entities.cleaningProcedureCodes} status={entities.cleaningProcedureCodesStatus}
              kind="cleaning procedure/checklist version"
            />
          );
        }
        if (f.type === "batchStepSelect") {
          return (
            <BatchStepSelectField
              key={f.name} label={f.label} required={f.required} hint={f.hint}
              value={values[f.name] ?? ""} onChange={(v) => setValue(f.name, v)}
              batchId={values[f.batchIdField ?? "batch_id"] ?? ""}
            />
          );
        }
        return (
          <Field key={f.name} label={f.label} required={f.required} hint={f.hint}>
            {f.type === "select" ? (
              <Select value={values[f.name] ?? ""} onChange={(e) => setValue(f.name, e.target.value)}>
 <option value="">Select</option>
                {(f.options ?? []).map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </Select>
            ) : f.type === "bool" ? (
              <Select value={values[f.name] ?? ""} onChange={(e) => setValue(f.name, e.target.value)}>
 <option value="">Select</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </Select>
            ) : f.type === "textarea" || f.type === "json" ? (
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
                type={f.type === "number" ? "number" : f.type === "date" ? "date" : "text"}
                value={values[f.name] ?? ""}
                onChange={(e) => setValue(f.name, e.target.value)}
                placeholder={f.placeholder}
              />
            )}
          </Field>
        );
      })}
    </>
  );
}

/** The shared "look up one operations record by id, view it, drive its workflow" page — used by the
 * WP-06 cleaning / EM / sterilization / aseptic screens, none of which have a list endpoint. */
export function OpsRecordPage<T extends { id: string; version: number }>({
  config,
  headerAction,
  afterHeader,
  collapseCreate,
  onCreated,
  detailInModal,
  hideLookup,
}: {
  config: OpsRecordConfig<T>;
  /** Extra control rendered next to the title (e.g. a "New <related master data>" button) — additive,
   * every existing caller omits it and gets the same header as before. */
  headerAction?: ReactNode;
  /** Rendered directly under the title/actions, above the create form and the lookup box — e.g. a
   * browsable list of related master data the caller wants visible as soon as the page opens, not
   * scrolled past. A plain `ReactNode` for a list unrelated to `T` (aseptic's profile list); or a
   * function receiving `openRecord` — this page's own by-id lookup, so a list of `T` itself (e.g.
   * sterilization's cycle list) can wire each row's "Open" button straight into it instead of the
   * caller re-implementing the lookup. Additive; every pre-existing caller passes a plain node. */
  afterHeader?: ReactNode | ((openRecord: (id: string) => void) => ReactNode);
  /** When true, `config.create`'s form moves behind a "+ <create label>" button next to `headerAction`
   * and opens in a Modal instead of always being expanded inline — useful once the page has other
   * content (like `afterHeader`) that should be the first thing visible. Defaults to false (every
   * existing caller keeps today's always-expanded inline form, unaffected). */
  collapseCreate?: boolean;
  /** Fired after a successful create AND after any transition completes (signed or not) — lets a
   * caller whose `afterHeader` lists `T` itself (e.g. sterilization's cycle list, aseptic's operation
   * list) refresh that list so a new row, or a row whose state/version just changed, shows up without
   * a manual page reload. Before 2026-10, this only fired on create — a transition only refreshed the
   * single open `record`, leaving the list behind it stale until the user reloaded the whole page (a
   * real user report, affecting every caller of this component the same way). Additive; omitted by
   * every pre-existing caller. */
  onCreated?: () => void;
  /** When true, an opened record (facts + extra + actions) renders in a `Modal` — closed by its own X —
   * instead of inline below the lookup box. Pairs with an `afterHeader` list whose "Open" button drives
   * `openRecord`, so opening a row reads as "view this record" rather than growing the page underneath
   * the list. Defaults to false (every pre-existing caller keeps today's inline rendering). */
  detailInModal?: boolean;
  /** When true, omits the "look up by id" card entirely — for a page whose `afterHeader` list already
   * covers every way in to a record (its own "Open" button), where a second manual-id lookup path is
   * redundant. Defaults to false (every pre-existing caller keeps the lookup box). */
  hideLookup?: boolean;
}) {
  const { me } = useMe();
  const { siteId } = useSiteId();
  const [id, setId] = useState("");
  const [record, setRecord] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createValues, setCreateValues] = useState<Record<string, string>>({});
  const [createComplexValues, setCreateComplexValues] = useState<Record<string, RepeatRow[] | KvRow[]>>({});
  const [createErr, setCreateErr] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);

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
      const values = parseValues(config.create.fields, createValues, createComplexValues);
      const receipt = await api.post<MutationReceipt>(config.create.path, {
        idempotency_key: newIdempotencyKey(),
        ...config.create.buildBody(values, siteId),
      });
      setCreateValues({});
      setCreateComplexValues({});
      load(receipt.aggregate_id);
      onCreated?.();
      if (collapseCreate) setCreateOpen(false);
    } catch (err) {
      if (err instanceof SyntaxError) setCreateErr(`Invalid JSON: ${err.message}`);
      else setCreateErr(err instanceof ApiError ? `${err.code}: ${err.message}` : "Create failed");
    } finally {
      setCreating(false);
    }
  }

  // `onCancel` is only passed by the Modal render site below — the inline (`!collapseCreate`) form has
  // nothing to cancel back to, so it renders without a Cancel button. Either way the submit button sits
  // at the end of its own row (via `justify-between` + a placeholder when there's no Cancel to balance
  // it), instead of flush left as a bare `<Button>` would otherwise render.
  function renderCreateForm(onCancel?: () => void) {
    if (!config.create) return null;
    return (
      <form onSubmit={create} className="grid grid-cols-2 gap-4 mt-3">
        <FieldInputs
          fields={config.create.fields}
          values={createValues}
          setValue={(n, v) => setCreateValues((c) => ({ ...c, [n]: v }))}
          complexValues={createComplexValues}
          setComplexValue={(n, v) => setCreateComplexValues((c) => ({ ...c, [n]: v }))}
        />
        <div style={{ gridColumn: "1 / -1" }}>
          {createErr && <p className="error-text mb-2">{createErr}</p>}
          <div className="flex justify-between gap-3">
            {onCancel ? (
              <Button type="button" variant="secondary" onClick={onCancel}>
                Cancel
              </Button>
            ) : (
              <span />
            )}
            <Button type="submit" variant="primary" disabled={creating}>
              {creating ? "Creating…" : config.create.label}
            </Button>
          </div>
        </div>
      </form>
    );
  }

  return (
    <div>
      <PageHead
        title={config.title}
        subtitle={config.subtitle}
        action={
          // A bare Fragment here would hoist headerAction and the create button as two separate
          // flex items of `.page-head` itself (`justify-content: space-between`) instead of a single
          // grouped item — with 3 items total (title, headerAction, create button) that spaces them
          // apart across the whole header instead of keeping the two actions together on the right.
          <div className="flex items-center gap-2">
            {headerAction}
            {collapseCreate && config.create && config.create.can(me) && (
              <Button variant="secondary" onClick={() => setCreateOpen(true)}>
                <Icon name="plus" /> {config.create.label}
              </Button>
            )}
          </div>
        }
      />

      {typeof afterHeader === "function" ? afterHeader(load) : afterHeader}

      {!collapseCreate && config.create && !config.create.can(me) && (
        <Banner tone="info" title="Read-only">
                {config.create.label} needs additional access - the lookup below still works for everyone.
        </Banner>
      )}

      {!collapseCreate && config.create && config.create.can(me) && (
        <Card pad className="mb-4">
          <CardHeader title={config.create.label} />
          {renderCreateForm()}
        </Card>
      )}

      {collapseCreate && createOpen && config.create && (
        <Modal open onClose={() => setCreateOpen(false)} title={config.create.label} large>
          {renderCreateForm(() => setCreateOpen(false))}
        </Modal>
      )}

      {!hideLookup && (
        <Card pad className="mb-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              load();
            }}
            className="flex flex-wrap items-end gap-3"
          >
            <Field label={config.idLabel}>
              <Input value={id} onChange={(e) => setId(e.target.value)} style={{ minWidth: 200, maxWidth: 320, width: "100%" }} />
            </Field>
            <Button type="submit" variant="secondary" disabled={loading || !id.trim()}>
              <Icon name="search" /> {loading ? "Loading…" : "Open"}
            </Button>
          </form>
          {error && <p className="error-text mt-3">{error}</p>}
        </Card>
      )}

      {record && (() => {
        const inStateNow = config.transitions.filter((t) => (t.show ? t.show(record) : true));
        const visible = inStateNow.filter((t) => (t.can ? t.can(me) : true));
        // Distinguishes the two reasons a record can show zero actions -- "nothing is valid from this
        // state" (every transition's own `show` excluded it) vs "something's valid but this user's role
        // doesn't grant it" -- so the empty case reads as an explanation, not a dead end (this is
        // exactly the gap a `show: (r) => r.state === "X"` guard opened: hiding a wrong-state action is
        // right, but landing on a record with none available and no reason given looks like a bug).
        const hiddenByRole = inStateNow.length > 0 && visible.length === 0;
        const actions = visible.length > 0 ? (
          <div className="flex flex-wrap gap-2 mt-3">
            {visible.map((t) => (
              <TransitionButton
                key={t.key}
                config={config}
                transition={t}
                record={record}
                onDone={() => {
                  load();
                  onCreated?.();
                }}
              />
            ))}
          </div>
        ) : (
          <p className="hint mt-2">
            {hiddenByRole
              ? "Your role doesn't grant any action available on this record right now."
              : `No action is available while this record is in its "${config.stateOf(record)}" state.`}
          </p>
        );

        if (detailInModal) {
          return (
            <Modal
              open
              onClose={() => setRecord(null)}
              large
              title={
                <span className="flex items-center gap-3">
                  {config.numberOf(record)} <WorkflowStatePill state={config.stateOf(record)} />
                </span>
              }
            >
              <FactGrid>{config.facts(record)}</FactGrid>
              {config.extra?.(record)}
              <CardHeader title="Actions" />
              {actions}
            </Modal>
          );
        }

        return (
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
              {actions}
            </Card>
          </>
        );
      })()}
    </div>
  );
}

function UnsignedTransition<T extends { id: string; version: number }>({
  config,
  transition,
  record,
  onDone,
  size,
}: {
  config: OpsRecordConfig<T>;
  transition: OpsTransitionDef<T>;
  record: T;
  onDone: () => void;
  size?: "sm" | "md" | "lg" | "icon";
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [complexValues, setComplexValues] = useState<Record<string, RepeatRow[] | KvRow[]>>({});
  return (
    <WorkflowActionButton
      size={size}
      label={transition.label}
      title={`${transition.label} - ${config.numberOf(record)}`}
      summary={transition.summary}
      confirmLabel={transition.label}
      variant={transition.variant ?? "secondary"}
      onDone={onDone}
      extraFields={
        transition.fields && transition.fields.length > 0 ? (
          <FieldInputs
            fields={transition.fields}
            values={values}
            setValue={(n, v) => setValues((c) => ({ ...c, [n]: v }))}
            complexValues={complexValues}
            setComplexValue={(n, v) => setComplexValues((c) => ({ ...c, [n]: v }))}
          />
        ) : undefined
      }
      onConfirm={() => {
        const parsed = parseValues(transition.fields ?? [], values, complexValues);
        return api.post<MutationReceipt>(`${config.apiRoot}/${record.id}/${transition.pathSegment ?? transition.key}`, {
          idempotency_key: newIdempotencyKey(),
          ...transition.buildBody(record, parsed),
        });
      }}
    />
  );
}

/** One transition (signed or not), fully self-contained — the single button + its own confirmation/
 * signature modal + field state. Used both for the detail view's "Actions" list (one `record` at a
 * time) and, exported, for a DataTable row's own quick-action buttons (one `record` per row, no need
 * to open the detail view first) — e.g. aseptic/page.tsx's "Record intervention"/"Record event"/
 * "Complete" per row, state-gated by the same `transition.show`/`.can` every other caller already
 * uses. Unsigned transitions delegate to `UnsignedTransition` unchanged; signed ones own a local
 * `open` flag and `SignatureCeremony` instead of the page-level `sigTransition` state this used to
 * require (removed — every transition button is now this same shape, so there's nothing page-level
 * left to coordinate). */
export function TransitionButton<T extends { id: string; version: number }>({
  config,
  transition,
  record,
  onDone,
  size,
}: {
  config: OpsRecordConfig<T>;
  transition: OpsTransitionDef<T>;
  record: T;
  onDone: () => void;
  /** Button size — e.g. "sm" for a compact DataTable row. Defaults to the normal `Button` size (used
   * by the detail view's "Actions" list). */
  size?: "sm" | "md" | "lg" | "icon";
}) {
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState<Record<string, string>>({});
  const [complexValues, setComplexValues] = useState<Record<string, RepeatRow[] | KvRow[]>>({});

  if (!transition.signed) {
    return <UnsignedTransition config={config} transition={transition} record={record} onDone={onDone} size={size} />;
  }

  return (
    <>
      <Button
        variant={transition.variant ?? "secondary"}
        size={size}
        onClick={() => {
          setValues({});
          setComplexValues({});
          setOpen(true);
        }}
      >
        {transition.label}
      </Button>
      {open && (
        <SignatureCeremony
          open
          onClose={() => setOpen(false)}
          onDone={() => {
            setOpen(false);
            onDone();
          }}
          challengePath={`${config.apiRoot}/${record.id}/signature-challenges`}
          action={transition.challengeAction ?? transition.key}
          title={`${transition.label} - ${config.numberOf(record)}`}
          summary={transition.summary}
          submitVariant={transition.variant === "danger" ? "danger" : transition.variant === "success" ? "success" : "primary"}
          extraFields={
            transition.fields && transition.fields.length > 0 ? (
              <FieldInputs
                fields={transition.fields}
                values={values}
                setValue={(n, v) => setValues((c) => ({ ...c, [n]: v }))}
                complexValues={complexValues}
                setComplexValue={(n, v) => setComplexValues((c) => ({ ...c, [n]: v }))}
              />
            ) : undefined
          }
          onSign={(p) => {
            const parsed = parseValues(transition.fields ?? [], values, complexValues);
            return api.post<MutationReceipt>(`${config.apiRoot}/${record.id}/${transition.pathSegment ?? transition.key}`, {
              idempotency_key: p.idempotency_key,
              challenge_id: p.challenge_id,
              reauth_password: p.reauth_password,
              ...transition.buildBody(record, parsed),
            });
          }}
        />
      )}
    </>
  );
}

export { Fact, IdFact } from "@/components/ui/FactGrid";
